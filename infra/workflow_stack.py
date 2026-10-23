from aws_cdk import (
    Stack,
    Duration,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
    aws_lambda as _lambda,
    aws_sqs as sqs,
    CfnOutput
)
from constructs import Construct

class WorkflowStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Dead Letter Queue for Failed Handler
        self.dlq = sqs.Queue(
            self, "WorkflowDLQ",
            retention_period=Duration.days(14)
        )

        # Common Lambda Environment
        common_env = {
            "STAGE": "production"
        }

        # 1. Lambdas for States
        validate_fn = _lambda.Function(
            self, "ValidateUploadFn",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler.validate_upload",
            code=_lambda.Code.from_inline("def validate_upload(e, c): return {'validated': True}"),
            timeout=Duration.seconds(30),
            environment=common_env
        )

        extract_fn = _lambda.Function(
            self, "ExtractFramesFn",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler.extract_frames",
            code=_lambda.Code.from_inline("def extract_frames(e, c): return {'frames': []}"),
            memory_size=3008,
            timeout=Duration.seconds(120),
            environment=common_env
        )

        classify_fn = _lambda.Function(
            self, "ClassifyViewpointsFn",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler.classify_viewpoints",
            code=_lambda.Code.from_inline("def classify_viewpoints(e, c): return {'coverage': 8}"),
            timeout=Duration.seconds(30),
            environment=common_env
        )

        damage_fn = _lambda.Function(
            self, "DamageDetectFn",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler.detect_damage",
            code=_lambda.Code.from_inline("def detect_damage(e, c): return {'findings': []}"),
            memory_size=3008,
            timeout=Duration.seconds(60),
            environment=common_env
        )

        cv_fn = _lambda.Function(
            self, "CvAnalyseFn",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler.cv_analyse",
            code=_lambda.Code.from_inline("def cv_analyse(e, c): return {'measurements': {}}"),
            memory_size=6144,
            timeout=Duration.seconds(180),
            environment=common_env
        )

        integrity_fn = _lambda.Function(
            self, "IntegrityCheckFn",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler.integrity_check",
            code=_lambda.Code.from_inline("def integrity_check(e, c): return {'trust': 'VERIFIED'}"),
            timeout=Duration.seconds(60),
            environment=common_env
        )

        compare_fn = _lambda.Function(
            self, "CompareBaselineFn",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler.compare_baseline",
            code=_lambda.Code.from_inline("def compare_baseline(e, c): return {'changes': []}"),
            timeout=Duration.seconds(60),
            environment=common_env
        )

        agent_review_fn = _lambda.Function(
            self, "AgentReviewFn",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler.agent_review",
            code=_lambda.Code.from_inline("def agent_review(e, c): return {'report': {}}"),
            timeout=Duration.seconds(60),
            environment=common_env
        )

        render_fn = _lambda.Function(
            self, "RenderReportFn",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler.render_report",
            code=_lambda.Code.from_inline("def render_report(e, c): return {'pdf': 'ok'}"),
            timeout=Duration.seconds(60),
            environment=common_env
        )

        finalise_fn = _lambda.Function(
            self, "FinaliseFn",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler.finalise",
            code=_lambda.Code.from_inline("def finalise(e, c): return {'status': 'DONE'}"),
            timeout=Duration.seconds(30),
            environment=common_env
        )

        # 2. Step Functions Task States
        validate_task = tasks.LambdaInvoke(self, "ValidateUpload", lambda_function=validate_fn, output_path="$.Payload")
        extract_task = tasks.LambdaInvoke(self, "ExtractFrames", lambda_function=extract_fn, output_path="$.Payload")
        classify_task = tasks.LambdaInvoke(self, "ClassifyViewpoints", lambda_function=classify_fn, output_path="$.Payload")

        # Parallel branches
        analyse_parallel = sfn.Parallel(self, "AnalyseParallel")
        damage_branch = tasks.LambdaInvoke(self, "DamageDetection", lambda_function=damage_fn, output_path="$.Payload")
        cv_branch = tasks.LambdaInvoke(self, "OpenCvAnalysis", lambda_function=cv_fn, output_path="$.Payload")
        integrity_branch = tasks.LambdaInvoke(self, "IntegrityChecks", lambda_function=integrity_fn, output_path="$.Payload")
        analyse_parallel.branch(damage_branch).branch(cv_branch).branch(integrity_branch)

        compare_task = tasks.LambdaInvoke(self, "CompareWithBaseline", lambda_function=compare_fn, output_path="$.Payload")
        agent_task = tasks.LambdaInvoke(self, "AgentReview", lambda_function=agent_review_fn, output_path="$.Payload")
        render_task = tasks.LambdaInvoke(self, "RenderReport", lambda_function=render_fn, output_path="$.Payload")
        finalise_task = tasks.LambdaInvoke(self, "Finalise", lambda_function=finalise_fn, output_path="$.Payload")

        # Wait for retake callback task
        wait_retake_task = sfn.Wait(self, "WaitForRetakeTask", time=sfn.WaitTime.duration(Duration.minutes(15)))

        # Retake Choice
        coverage_choice = sfn.Choice(self, "CoverageChoice")
        all_covered_condition = sfn.Condition.or_(
            sfn.Condition.number_equals("$.coverage", 8),
            sfn.Condition.number_greater_than_equals("$.retakeRounds", 2)
        )

        coverage_choice.when(all_covered_condition, analyse_parallel)
        coverage_choice.otherwise(wait_retake_task.next(analyse_parallel))

        # Comparison Choice
        comparison_choice = sfn.Choice(self, "ComparisonChoice")
        is_comparison_condition = sfn.Condition.string_equals("$.type", "COMPARISON")
        comparison_choice.when(is_comparison_condition, compare_task.next(agent_task))
        comparison_choice.otherwise(agent_task)

        # Assemble State Machine Definition
        definition = validate_task.next(extract_task).next(classify_task).next(coverage_choice)
        analyse_parallel.next(comparison_choice)
        agent_task.next(render_task).next(finalise_task)

        self.state_machine = sfn.StateMachine(
            self, "CarCheckProcessingStateMachine",
            definition=definition,
            state_machine_type=sfn.StateMachineType.STANDARD,
            timeout=Duration.minutes(15),
            tracing_enabled=True
        )

        CfnOutput(self, "StateMachineArn", value=self.state_machine.state_machine_arn)

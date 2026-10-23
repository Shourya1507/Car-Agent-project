from aws_cdk import (
    Stack,
    Duration,
    aws_cloudwatch as cloudwatch,
    aws_logs as logs,
    CfnOutput
)
from constructs import Construct

class ObservabilityStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # 1. Structured JSON Log Group
        self.log_group = logs.LogGroup(
            self, "CarCheckLogGroup",
            log_group_name="/aws/carcheck/pipeline",
            retention=logs.RetentionDays.ONE_MONTH
        )

        # 2. Key Metrics per TRD Section 14
        latency_metric = cloudwatch.Metric(
            namespace="CarCheck/Pipeline",
            metric_name="StageLatency",
            statistic="p95",
            period=Duration.minutes(5)
        )

        failure_metric = cloudwatch.Metric(
            namespace="CarCheck/Pipeline",
            metric_name="WorkflowFailureRate",
            statistic="Sum",
            period=Duration.minutes(5)
        )

        # 3. Alarms
        self.latency_alarm = cloudwatch.Alarm(
            self, "PipelineP95LatencyAlarm",
            metric=latency_metric,
            threshold=90.0, # Alert if p95 latency exceeds 90s (TRD 14)
            evaluation_periods=2,
            alarm_description="Alert when CarCheck processing p95 latency exceeds 90 seconds"
        )

        self.failure_alarm = cloudwatch.Alarm(
            self, "PipelineFailureRateAlarm",
            metric=failure_metric,
            threshold=3.0,
            evaluation_periods=1,
            alarm_description="Alert on high workflow failure count"
        )

        CfnOutput(self, "LogGroupName", value=self.log_group.log_group_name)

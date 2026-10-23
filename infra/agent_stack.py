from aws_cdk import (
    Stack,
    aws_iam as iam,
    aws_bedrock as bedrock,
    CfnOutput
)
from constructs import Construct

class AgentStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Bedrock Agent Execution Role
        self.agent_role = iam.Role(
            self, "CarCheckBedrockAgentRole",
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com"),
            description="IAM role for CarCheck Bedrock reasoning agent"
        )

        self.agent_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream"
                ],
                resources=["*"]
            )
        )

        # Bedrock Guardrail to prevent defamatory claims and ensure screening disclaimer grounding
        self.guardrail = bedrock.CfnGuardrail(
            self, "CarCheckGuardrail",
            name="CarCheckGroundingGuardrail",
            description="Ensures agent statements cite findings and never assert unproven legal liability",
            blocked_input_messaging="Your request violates vehicle inspection screening safety guidelines.",
            blocked_outputs_messaging="Inspection screening safety: findings must be verified by a mechanic.",
            content_policy_config=bedrock.CfnGuardrail.ContentPolicyConfigProperty(
                filters_config=[
                    bedrock.CfnGuardrail.FilterConfigProperty(
                        input_strength="HIGH",
                        output_strength="HIGH",
                        type="HATE"
                    ),
                    bedrock.CfnGuardrail.FilterConfigProperty(
                        input_strength="HIGH",
                        output_strength="HIGH",
                        type="INSULTS"
                    )
                ]
            )
        )

        CfnOutput(self, "BedrockAgentRoleArn", value=self.agent_role.role_arn)
        CfnOutput(self, "GuardrailId", value=self.guardrail.attr_guardrail_id)

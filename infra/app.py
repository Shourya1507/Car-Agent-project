#!/usr/bin/env python3
import aws_cdk as cdk
from storage_stack import StorageStack
from auth_stack import AuthStack
from agent_stack import AgentStack
from workflow_stack import WorkflowStack
from api_stack import ApiStack
from observability_stack import ObservabilityStack

app = cdk.App()

env = cdk.Environment(
    account=app.node.try_get_context("account"),
    region=app.node.try_get_context("region") or "us-east-1"
)

# 1. Storage & Encryption Keys
storage_stack = StorageStack(app, "CarCheckStorageStack", env=env)

# 2. Authentication (Cognito)
auth_stack = AuthStack(app, "CarCheckAuthStack", env=env)

# 3. Agentic AI Reasoning (Bedrock Agent)
agent_stack = AgentStack(app, "CarCheckAgentStack", env=env)

# 4. Step Functions Workflow
workflow_stack = WorkflowStack(app, "CarCheckWorkflowStack", env=env)

# 5. Edge and API Gateway
api_stack = ApiStack(
    app, "CarCheckApiStack",
    user_pool=auth_stack.user_pool,
    user_pool_client=auth_stack.user_pool_client,
    env=env
)

# 6. Observability & Monitoring
observability_stack = ObservabilityStack(app, "CarCheckObservabilityStack", env=env)

app.synth()

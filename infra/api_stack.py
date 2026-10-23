from aws_cdk import (
    Stack,
    Duration,
    aws_apigatewayv2 as apigw,
    aws_apigatewayv2_integrations as integrations,
    aws_apigatewayv2_authorizers as authorizers,
    aws_lambda as _lambda,
    CfnOutput
)
from constructs import Construct

class ApiStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        user_pool,
        user_pool_client,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # 1. API Gateway HTTP API
        self.http_api = apigw.HttpApi(
            self, "CarCheckHttpApi",
            api_name="CarCheckApi",
            cors_preflight=apigw.CorsPreflightOptions(
                allow_origins=["*"],
                allow_methods=[apigw.CorsHttpMethod.ANY],
                allow_headers=["*"],
                max_age=Duration.days(10)
            )
        )

        # 2. Cognito JWT Authorizer
        authorizer = authorizers.HttpUserPoolAuthorizer(
            "CognitoAuthorizer",
            pool=user_pool,
            user_pool_clients=[user_pool_client]
        )

        # 3. Main API Lambda
        api_lambda = _lambda.Function(
            self, "CarCheckApiHandler",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="main.handler",
            code=_lambda.Code.from_asset("backend"),
            memory_size=1024,
            timeout=Duration.seconds(30)
        )

        lambda_integration = integrations.HttpLambdaIntegration(
            "ApiLambdaIntegration",
            handler=api_lambda
        )

        # 4. Authenticated Routes (TRD Section 9)
        auth_routes = [
            ("POST", "/inspections"),
            ("POST", "/inspections/{id}/start"),
            ("GET", "/inspections"),
            ("GET", "/inspections/{id}"),
            ("POST", "/inspections/{id}/retake"),
            ("GET", "/inspections/{id}/report.pdf"),
            ("POST", "/inspections/{id}/share"),
            ("GET", "/inspections/{id}/challenge"),
            ("GET", "/inspections/{id}/comparison"),
            ("DELETE", "/inspections/{id}")
        ]

        for method, path in auth_routes:
            http_method = getattr(apigw.HttpMethod, method)
            self.http_api.add_routes(
                path=path,
                methods=[http_method],
                integration=lambda_integration,
                authorizer=authorizer
            )

        # 5. Public Routes (no authentication required)
        public_routes = [
            ("GET", "/reports/{id}/verify"),
            ("GET", "/share/{token}")
        ]

        for method, path in public_routes:
            http_method = getattr(apigw.HttpMethod, method)
            self.http_api.add_routes(
                path=path,
                methods=[http_method],
                integration=lambda_integration
            )

        CfnOutput(self, "HttpApiUrl", value=self.http_api.api_endpoint)

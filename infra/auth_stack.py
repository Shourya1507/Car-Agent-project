from aws_cdk import (
    Stack,
    RemovalPolicy,
    aws_cognito as cognito,
)
from constructs import Construct

class AuthStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.user_pool = cognito.UserPool(
            self, "CarCheckUserPool",
            user_pool_name="carcheck-users",
            self_sign_up_enabled=True,
            sign_in_aliases=cognito.SignInAliases(email=True),
            auto_verify=cognito.AutoVerifiedAttrs(email=True),
            password_policy=cognito.PasswordPolicy(
                min_length=8,
                require_digits=True,
                require_lowercase=True,
                require_uppercase=True
            ),
            removal_policy=RemovalPolicy.DESTROY
        )

        self.user_pool_client = self.user_pool.add_client(
            "CarCheckWebClient",
            user_pool_client_name="carcheck-pwa-client",
            auth_flows=cognito.AuthFlow(
                user_password=True,
                user_srp=True
            ),
            generate_secret=False
        )

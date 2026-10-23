from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    aws_s3 as s3,
    aws_dynamodb as dynamodb,
    aws_kms as kms,
)
from constructs import Construct

class StorageStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # 1. KMS Keys
        # Symmetric key for S3 bucket encryption
        self.s3_key = kms.Key(
            self, "CarCheckStorageKey",
            description="KMS Key for CarCheck private storage bucket",
            enable_key_rotation=True,
            removal_policy=RemovalPolicy.DESTROY
        )

        # Asymmetric key for ECDSA P-256 report signing (TRD Section 11)
        self.signing_key = kms.Key(
            self, "CarCheckReportSigningKey",
            description="Asymmetric ECDSA P-256 Key for signing condition reports",
            key_spec=kms.KeySpec.ECC_NIST_P256,
            key_usage=kms.KeyUsage.SIGN_VERIFY,
            removal_policy=RemovalPolicy.RETAIN
        )

        # 2. Private S3 Bucket with Lifecycle Rules
        self.bucket = s3.Bucket(
            self, "CarCheckBucket",
            encryption=s3.BucketEncryption.KMS,
            encryption_key=self.s3_key,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="ExpireRawVideo1Day",
                    prefix="raw/",
                    expiration=Duration.days(1)
                ),
                s3.LifecycleRule(
                    id="ExpireFrames7Days",
                    prefix="frames/",
                    expiration=Duration.days(7)
                )
            ],
            cors=[
                s3.CorsRule(
                    allowed_methods=[s3.HttpMethods.PUT, s3.HttpMethods.GET],
                    allowed_origins=["*"],
                    allowed_headers=["*"],
                    max_age=3600
                )
            ]
        )

        # 3. DynamoDB Tables (On-Demand Capacity per TRD Section 4 & 10)
        self.inspections_table = dynamodb.Table(
            self, "InspectionsTable",
            partition_key=dynamodb.Attribute(name="userId", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="inspectionId", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            point_in_time_recovery=True,
            removal_policy=RemovalPolicy.DESTROY
        )
        self.inspections_table.add_global_secondary_index(
            index_name="StatusIndex",
            partition_key=dynamodb.Attribute(name="status", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="createdAt", type=dynamodb.AttributeType.STRING)
        )

        self.findings_table = dynamodb.Table(
            self, "FindingsTable",
            partition_key=dynamodb.Attribute(name="inspectionId", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="findingId", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY
        )

        self.captures_table = dynamodb.Table(
            self, "CapturesTable",
            partition_key=dynamodb.Attribute(name="inspectionId", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="viewpoint", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY
        )

        self.challenges_table = dynamodb.Table(
            self, "ChallengesTable",
            partition_key=dynamodb.Attribute(name="inspectionId", type=dynamodb.AttributeType.STRING),
            time_to_live_attribute="expiresAt",
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY
        )

        self.share_links_table = dynamodb.Table(
            self, "ShareLinksTable",
            partition_key=dynamodb.Attribute(name="token", type=dynamodb.AttributeType.STRING),
            time_to_live_attribute="expiresAt",
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY
        )

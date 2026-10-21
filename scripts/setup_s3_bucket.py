#!/usr/bin/env python3
"""Create a new private S3 bucket using an already configured AWS profile."""

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cowingman.memory import S3SummaryStore
from cowingman.errors import ConfigurationError


def create(client, bucket, region):
    # In us-east-1 CreateBucket can succeed for an already-owned bucket; refuse it.
    try:
        client.head_bucket(Bucket=bucket)
    except Exception as exc:
        response = getattr(exc, "response", {})
        if response.get("ResponseMetadata", {}).get("HTTPStatusCode") != 404:
            raise ConfigurationError(
                "Cannot verify that the bucket name is unused. Check access or choose another name."
            ) from None
    else:
        raise ConfigurationError(
            "Bucket already exists; choose a new name or use the existing bucket without this setup script."
        )
    args = {"Bucket": bucket, "ObjectOwnership": "BucketOwnerEnforced"}
    if region != "us-east-1":
        args["CreateBucketConfiguration"] = {"LocationConstraint": region}
    client.create_bucket(**args)
    client.put_public_access_block(
        Bucket=bucket,
        PublicAccessBlockConfiguration={
            "BlockPublicAcls": True,
            "IgnorePublicAcls": True,
            "BlockPublicPolicy": True,
            "RestrictPublicBuckets": True,
        },
    )
    client.put_bucket_encryption(
        Bucket=bucket,
        ServerSideEncryptionConfiguration={
            "Rules": [
                {
                    "ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"},
                }
            ]
        },
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bucket", required=True, help="new globally unique bucket name")
    parser.add_argument("--region", required=True)
    args = parser.parse_args()
    try:
        store = S3SummaryStore("s3://" + args.bucket + "/cowingman/jetson", args.region)
        create(store.client, store.bucket, args.region)
    except ConfigurationError as exc:
        print(str(exc))
        return 2
    except Exception:
        print("Bucket setup did not finish. Check AWS permissions and bucket-name availability.")
        print(
            "If a bucket was created, verify Block Public Access and encryption in S3 before upload."
        )
        return 1
    print("Private bucket created with ACLs disabled, Block Public Access and SSE-S3 encryption.")
    print("Grant the runtime identity this limited policy (attach through IAM):")
    print(
        json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": ["s3:GetObject", "s3:PutObject"],
                        "Resource": f"arn:aws:s3:::{args.bucket}/cowingman/jetson/*",
                    }
                ],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

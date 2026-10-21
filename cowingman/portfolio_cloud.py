"""Explicit private S3 portfolio storage; retrieval remains local during conversation."""

import argparse
import json
import re
from uuid import uuid4

from .errors import CloudRequestError, ConfigurationError
from .memory import S3SummaryStore, stamp, utc_now
from .portfolio import Portfolio, MAX_FILE_BYTES
from .timing import NO_TIMING


class S3PortfolioStore(S3SummaryStore):
    def __init__(self, uri, region, *, client=None, timing=NO_TIMING):
        super().__init__(uri, region, client=client, timing=timing)

    def upload(self, portfolio):
        body = json.dumps(
            {
                "version": 1,
                "created_at": stamp(utc_now()),
                "passages": [{"text": text} for text in portfolio.passages],
            },
            ensure_ascii=False,
        ).encode("utf-8")
        Portfolio.from_bytes(body)
        key = "portfolios/" + stamp(utc_now()).replace(":", "-") + "-" + uuid4().hex + ".json"
        try:
            with self.timing.measure("s3_upload"):
                for name in (key, "portfolio.json"):
                    self.client.put_object(
                        Bucket=self.bucket,
                        Key=self.prefix + "/" + name,
                        Body=body,
                        ContentType="application/json",
                        ServerSideEncryption="AES256",
                    )
        except Exception:
            raise CloudRequestError(
                "S3 portfolio upload failed. Check AWS access and region."
            ) from None
        return key

    def load(self, key="portfolio.json"):
        if not re.fullmatch(r"portfolio\.json|portfolios/[A-Za-z0-9_-]+\.json", key):
            # Timestamp names include a decimal point before milliseconds.
            if not re.fullmatch(r"portfolios/[A-Za-z0-9_.-]+\.json", key):
                raise ConfigurationError("Use portfolio.json or a portfolios/ archive key.")
        body = None
        try:
            with self.timing.measure("s3_load"):
                response = self.client.get_object(Bucket=self.bucket, Key=self.prefix + "/" + key)
                body = response["Body"]
                return Portfolio.from_bytes(body.read(MAX_FILE_BYTES + 1))
        except Exception:
            raise ConfigurationError(
                "Cannot load S3 portfolio. Check access, region and file format."
            ) from None
        finally:
            if body is not None:
                body.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("upload", "check"))
    parser.add_argument("--s3", required=True, help="S3 prefix, e.g. s3://bucket/cowingman/jetson")
    parser.add_argument("--aws-region", required=True)
    parser.add_argument("--portfolio", help="local portfolio JSON to upload")
    args = parser.parse_args(argv)
    if args.action == "upload" and not args.portfolio:
        parser.error("upload requires --portfolio")
    try:
        store = S3PortfolioStore(args.s3, args.aws_region)
        if args.action == "upload":
            portfolio = Portfolio.load(args.portfolio)
            store.upload(portfolio)
            print("Portfolio saved to S3: timestamped archive and portfolio.json.")
        else:
            portfolio = store.load()
            print(f"S3 portfolio validated: {len(portfolio.passages)} passages. Content hidden.")
        return 0
    except (ConfigurationError, CloudRequestError) as exc:
        print(str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

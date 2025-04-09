from enum import StrEnum


class TrustedHeader(StrEnum):
    X_FORWARDED_FOR = "x-forwarded-for"
    X_FORWARDED_HOST = "x-forwarded-host"
    X_FORWARDED_PORT = "x-forwarded-port"
    X_FORWARDED_PROTO = "x-forwarded-proto"
    X_FORWARDED_PREFIX = "x-forwarded-prefix"
    X_FORWARDED_AWS_ELB = "x-forwarded-aws-elb"
    FORWARDED = "forwarded"

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

resource "aws_dynamodb_table" "assignments" {
  name         = "duesoon-assignments"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "assignment_id"

  attribute {
    name = "assignment_id"
    type = "S"
  }
}
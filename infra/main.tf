# iceOS simple AWS ECS deployment – single file for ease of use

terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

variable "region" {
  description = "AWS region"
  type        = string
}

variable "image" {
  description = "Full container image (ECR or DockerHub)"
  type        = string
}

variable "desired_count" {
  description = "Number of tasks"
  type        = number
  default     = 1
}

provider "aws" {
  region = var.region
}

module "network" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.0.0"

  name = "iceos-vpc"
  cidr = "10.44.0.0/16"

  azs             = ["${var.region}a", "${var.region}b"]
  public_subnets  = ["10.44.1.0/24", "10.44.2.0/24"]
  private_subnets = ["10.44.101.0/24", "10.44.102.0/24"]
}

module "ecs_cluster" {
  source  = "terraform-aws-modules/ecs/aws"
  version = "5.0.0"

  name   = "iceos-cluster"
  vpc_id = module.network.vpc_id
}

module "ecs_service" {
  source  = "terraform-aws-modules/ecs/aws//modules/service"
  version = "5.0.0"

  name        = "iceos-api"
  cluster_arn = module.ecs_cluster.cluster_arn
  launch_type = "FARGATE"

  cpu           = 512
  memory        = 1024
  desired_count = var.desired_count

  subnet_ids = module.network.private_subnets

  container_definitions = jsonencode([
    {
      name      = "iceos"
      image     = var.image
      essential = true
      portMappings = [
        { containerPort = 8000, hostPort = 8000 }
      ]
    }
  ])
}

output "load_balancer_url" {
  description = "Public URL of the service"
  value       = module.ecs_service.lb_dns_name
} 
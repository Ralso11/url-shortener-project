output "api_url" {
  description = "Base URL of the URL shortener API"
  value       = aws_apigatewayv2_stage.default.invoke_url
}

output "dynamodb_table_name" {
  description = "Name of the DynamoDB table storing URL mappings"
  value       = aws_dynamodb_table.urls.name
}

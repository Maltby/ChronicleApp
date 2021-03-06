# AWS Lambda Functions

Chronicle uses AWS Lambda functions to securely and reliably perform queries for the iOS client. Once the client makes an AWS API Gateway request, the gateway will route the request to AWS Lambda, returning the desired results.

AWS Lambda functions include three input variables; event, context, and callback. The “event” contains information passed through API Gateway, including a user’s id or a search query if necessary. The “context” generally contains information about the request, such as platform and user info (in our case user info is passed though the “event”). Finally, the “callback” variable is used to return information to the caller. Once API Gateway receives the callback, the results are mapped using a JSON schema and passed through to the iOS client.
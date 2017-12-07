Chronicle is an iOS application for listening to copyright free audio books, backed by AWS.

AWS services used include:
>Lambda
>iAM
>RDS (PostgreSQL)
>API Gateway
>Cognito
>S3
>Polly

To begin, a Gutenberg repo was used to pull metadata for all 58,000+ currently available books. A python script than ran locally, pulling an HTML representation for the book then formatting the book into chapters. Chapters were transcribed using AWS Polly and uploaded to AWS S3.

AWS API Gateway offered a way to securely give Cognito users (on iOS) access to AWS Lambda functions. After setting up each gateway route, AWS API Gateway would automatically creates SDK to give the client (iOS) access to the routes. 

AWS Lambda functions include querying the AWS RDS PostgreSQL “booksmain” table, returning most popular books or search results. Another function is able to query the “usersmain” database, returning a list of the users favorite books.

AWS iAM was used to give AWS tools access to one another. The API Gateway role needed to be able to access Lambda functions, the Lambda functions needed access to the RDS instance, etc.

An AWS Cognito user pool was used on iOS to give users access to the API Gateway, ensuring that no non-members are able to make gateway, and therefor Lambda calls. To access the secured audio files on S3, an AWS S3 pre-signed URL was used, giving the iOS user the ability to seamlessly download and listen to books.

Usage:
iOS
cd to Chronicle/ and “pod install”.
In order to build, valid AWS credentials must be input into Helpers/Secrets.swift: 
	Uncomment code within “SecretsExample.swift”.
	Rename “SecretsExample.swift” to “Secrets.swift”.
	Fill dictionaries with valid AWS credentials.
Python
Scripts pass AWS CLI credentials to boto3, allowing for access to AWS services:
	Install the AWS CLI.
	Run “aws configure” and input valid credentials.
	Both will now use the credentials entered within the CLI to run scripts.
Node.js Lambda Functions
cd into each lambda function and run “npm install”
In order to run, “secrets.js” must be configured:
	Rename each “secretsExample.js” to “secrets.js”.
	Within each “secrets.js”, input valid AWS credentials.

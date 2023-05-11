import boto3
import os
import datetime
import csv

def lambda_handler(event, context):

    # Get all Lambda functions
    client = boto3.client('lambda')
    functions = client.list_functions()['Functions']

    # Define variables for the headings
    IDENTIFIER = "Identifier"
    SERVICE = "Service"
    FUNCTION_NAME = "Function Name"
    DESCRIPTION = "Description"
    REGION = "Region"
    RUNTIME = "Runtime"
    MEMORY = "Memory (MB)"
    TIMEOUT = "Timeout (s)"
    LAST_MODIFIED = "Last Modified"
    CODE_SIZE = "Code Size (bytes)"
    ENV_VARS = "Environment Variables"
    TAGS = "Tags"

    # Initialize an empty array to store all function details
    function_details = []

    # Iterate over each function
    for function in functions:
        # Get the tags for the function
        tags = function.get('Tags', [])

        # Get the function metadata
        function_dict = {}
        function_dict[IDENTIFIER] = function['FunctionName']
        function_dict[SERVICE] = "Lambda"
        function_dict[FUNCTION_NAME] = function['FunctionName']
        function_dict[DESCRIPTION] = client.get_function(FunctionName=function['FunctionName'])['Configuration']['Description']
        function_dict[REGION] = function['FunctionArn'].split(':')[3]
        function_dict[RUNTIME] = function['Runtime']
        function_dict[MEMORY] = function['MemorySize']
        function_dict[TIMEOUT] = function['Timeout']
        function_dict[LAST_MODIFIED] = str(datetime.datetime.strptime(function['LastModified'], '%Y-%m-%dT%H:%M:%S.%f%z').strftime('%d-%m-%y %H:%M:%S'))
        function_dict[CODE_SIZE] = function['CodeSize']
        function_dict[ENV_VARS] = '|'.join([f"{key}:{value}" for key, value in function.get('Environment', {}).get('Variables', {}).items()]) or 'NA'
        function_dict[TAGS] = '|'.join([f"{tag.get('Key', 'NA')}:{tag.get('Value', 'NA')}" for tag in tags])
        
        function_details.append(function_dict)

    # Write the function details to a CSV file with timestamp in the filename
    IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
    timestamp_filename = f"/tmp/Lambda-Inventory-{datetime.datetime.now(IST).strftime('%d-%m-%Y-%H-%M-%S')}.csv"
    with open(timestamp_filename, 'w') as csv_file:
        fieldnames = [IDENTIFIER, SERVICE, FUNCTION_NAME, DESCRIPTION, REGION, RUNTIME, MEMORY, TIMEOUT, LAST_MODIFIED, CODE_SIZE, ENV_VARS, TAGS]
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for function in function_details:
            writer.writerow(function)

    # Upload the CSV file with timestamp to S3
    s3 = boto3.client('s3')
    bucket_name = "bucketinventorymanagement"
    folder_name = 'InventoryDetails'
    if folder_name:
        s3.put_object(Bucket=bucket_name, Key=(folder_name+'/'))

    s3.upload_file(timestamp_filename, bucket_name, folder_name + '/' + os.path.basename(timestamp_filename))

    # Write the function details to a CSV file with fixed name
    fixed_filename = "/tmp/Latest-LambdaInventory.csv"
    with open(fixed_filename, 'w') as csv_file:
        fieldnames = [IDENTIFIER, SERVICE, FUNCTION_NAME, DESCRIPTION, REGION, RUNTIME, MEMORY, TIMEOUT, LAST_MODIFIED, CODE_SIZE, ENV_VARS, TAGS]
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for function in function_details:
            writer.writerow(function)

    # Upload the CSV file with fixed name to S3
    s3.upload_file(fixed_filename, bucket_name, folder_name + '/Latest-LambdaInventory.csv')

    return {
        'statusCode': 200,
        'body': f'Lambda Inventory files "{timestamp_filename}" and "{fixed_filename}" successfully generated and uploaded to S3 bucket "{bucket_name}"'
    }

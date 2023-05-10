import boto3
import os
import datetime
import csv
import botocore

IDENTIFIER = "Identifier"  
SERVICE = "Service"  
BUCKET_NAME = "Bucket Name" 
REGION = "Region"  
CREATION_DATE = "Creation Date"
STORAGE_CLASS = "Storage Class"  
OBJECT_COUNT = "Object Count"
TOTAL_SIZE = "Total Size (bytes)"
TAGS = "Tags"   

def lambda_handler(event, context):
    """
    Generates an S3 inventory report and uploads it to an S3 bucket.
    
    Input: None
    Output: None 
    """
    
    # Get all S3 buckets
    s3 = boto3.resource('s3')
    buckets = s3.buckets.all() 

    # Initialize an empty array to store all bucket details
    bucket_details = []

    # Iterate over each bucket
    for bucket in buckets:
        # Get the tags for the bucket
        try:
            tags = s3.BucketTagging(bucket.name).tag_set
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchTagSet':
                tags = []
            else:
                raise e
        
        # Get the bucket storage class 
        storage_class = s3.BucketVersioning(bucket.name).status 
        
        # Get the total size of the objects in the bucket
        total_size = sum(obj.size for obj in bucket.objects.all())  
        
        # Get the bucket metadata
        bucket_dict = {}  
        bucket_dict[IDENTIFIER] = bucket.name
        bucket_dict[SERVICE] = "S3" 
        bucket_dict[BUCKET_NAME] = bucket.name  
        bucket_dict[REGION] = s3.meta.client.get_bucket_location(Bucket=bucket.name)['LocationConstraint']
        bucket_dict[CREATION_DATE] = str(bucket.creation_date.strftime('%d-%m-%y %H:%M:%S'))
        bucket_dict[STORAGE_CLASS] = storage_class 
        bucket_dict[OBJECT_COUNT] = len(list(bucket.objects.all()))
        bucket_dict[TOTAL_SIZE] = total_size
        bucket_dict[TAGS] = '|'.join([f"{tag['Key']}:{tag['Value']}" for tag in tags]) 
        
        # Add the bucket details to the bucket_details list
        bucket_details.append(bucket_dict)

    # Write the bucket details to a CSV file
    IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
    filename = f"/tmp/S3-Inventory-{datetime.datetime.now(IST).strftime('%d-%m-%Y-%H-%M-%S')}.csv"
    with open(filename, 'w') as csv_file:
        fieldnames = [IDENTIFIER, SERVICE, BUCKET_NAME, REGION, CREATION_DATE,STORAGE_CLASS,  OBJECT_COUNT, TOTAL_SIZE, TAGS]
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for bucket in bucket_details:
            writer.writerow(bucket)

    # Upload the CSV file to S3
    bucket_name = "bucketinventorymanagement"
    s3.Bucket(bucket_name).upload_file(filename, f"InventoryDetails/{os.path.basename(filename)}")
    return {
        'statusCode': 200,
        'body': f'S3 Inventory file "{filename}" successfully generated and uploaded to S3 bucket "{bucket_name}"'
    }

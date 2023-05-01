import boto3
import os
import datetime
import csv

def lambda_handler(event, context):
    
    # Get all EC2 instances
    instances = get_all_ec2_instances()

    # Define variables for the headings
    IDENTIFIER = "Identifier"
    SERVICE = "Service"
    INSTANCE_ID = "Instance ID"
    REGION = "Region"
    INSTANCE_TYPE = "Instance Type"
    LAUNCH_TIME = "Launch Time"
    CREATION_TIME = "Creation Time"
    DELETION_TIME = "Deletion Time"
    PRIVATE_IP = "Private IP Address"
    PUBLIC_IP = "Public IP Address"
    OS_VERSION = "OS Version"
    IAM_ROLE = "IAM Role"
    DISK_USAGE = "Disk Usage (GiB)"
    CPU = "CPU (vCPUs)"
    RAM = "RAM (GiB)"
    TAGS = "Tags"

    # Initialize an empty array to store all instance details
    instance_details = []

    # Iterate over each instance
    for reservation in instances['Reservations']:
        for instance in reservation['Instances']:
            # Get the tags for the instance
            tags = instance.get('Tags', [])
        
            # Check if the instance has the required tags
            if 'Project' not in [tag['Key'] for tag in tags] or 'Environment' not in [tag['Key'] for tag in tags]:
                continue
        
            # Get the tags dictionary for the instance
            tags_dict = {tag['Key']: tag['Value'] for tag in tags}
            
            # Join tags with a pipe delimiter
            tags_str = '|'.join([f"{tag['Key']}:{tag['Value']}" for tag in tags])
        
            # Get the instance metadata
            instance_dict = {}
            instance_dict[IDENTIFIER] = f"{tags_dict['Project']} - {tags_dict['Environment']}"
            instance_dict[SERVICE] = "EC2"
            instance_dict[INSTANCE_ID] = instance['InstanceId']
            instance_dict[REGION] = instance['Placement']['AvailabilityZone'][:-1]
            instance_dict[INSTANCE_TYPE] = instance['InstanceType']
            instance_dict[LAUNCH_TIME] = str(instance['LaunchTime'].strftime('%d-%m-%y'))
            instance_dict[CREATION_TIME] = str(instance['CreateTime'].strftime('%d-%m-%y %H:%M:%S')) if 'CreateTime' in instance else 'NA'
            instance_dict[DELETION_TIME] = str(instance['StateTransitionReason']).split()[-3] if 'StateTransitionReason' in instance and 'deleting' in instance['StateTransitionReason'] else 'NA'
            instance_dict[PRIVATE_IP] = instance.get('PrivateIpAddress', '')
            instance_dict[PUBLIC_IP] = instance.get('PublicIpAddress', '')
            instance_dict[OS_VERSION] = instance['Platform'] if 'Platform' in instance else instance['ImageId']
            instance_dict[IAM_ROLE] = instance['IamInstanceProfile']['Arn'].split('/')[1] if 'IamInstanceProfile' in instance else 'NA'
            instance_dict[DISK_USAGE] = get_disk_usage(instance['InstanceId'])
            instance_dict[CPU] = get_instance_resources(instance['InstanceId'])[CPU]
            instance_dict[RAM] = get_instance_resources(instance['InstanceId'])[RAM]
            instance_dict[TAGS] = tags_str
        
            instance_details.append(instance_dict)


            # Write the instance details to a CSV file
        IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
        filename = f"/tmp/EC2-Inventory-{datetime.datetime.now(IST).strftime('%d-%m-%Y-%H-%M-%S')}.csv"
        with open(filename, 'w') as csv_file:
            fieldnames = [IDENTIFIER, SERVICE, INSTANCE_ID, REGION, INSTANCE_TYPE, LAUNCH_TIME, CREATION_TIME, DELETION_TIME, PRIVATE_IP, PUBLIC_IP, OS_VERSION, IAM_ROLE, DISK_USAGE, CPU, RAM, TAGS]
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()
            for instance in instance_details:
                writer.writerow(instance)

    # Upload the CSV file to S3
    s3 = boto3.client('s3')
    bucket_name = "bucketinventorymanagement"
    folder_name = 'InventoryDetails'  # Replace with your desired folder name
    if folder_name:
        s3.put_object(Bucket=bucket_name, Key=(folder_name+'/'))

    s3.upload_file(filename, bucket_name, folder_name + '/' + os.path.basename(filename))
    return {
        'statusCode': 200,
        'body': f'EC2 Inventory file "{filename}" successfully generated and uploaded to S3 bucket "{bucket_name}"'
    }

def get_all_ec2_instances():
    #Returns a dictionary containing all EC2 instances in the current region.
    ec2 = boto3.client('ec2')
    return ec2.describe_instances() #get all the metadata for all instances in the account.


def get_disk_usage(instance_id):
    ec2 = boto3.resource('ec2')
    instance = ec2.Instance(instance_id)
    total_size = 0
    for volume in instance.volumes.all():
        total_size += volume.size
    return total_size

def get_instance_resources(instance_id):
    ec2 = boto3.resource('ec2')
    instance = ec2.Instance(instance_id)
    return {
        "CPU (vCPUs)": instance.cpu_options['CoreCount'] if instance.cpu_options is not None else 'NA',
        "RAM (GiB)": instance.instance_type.split('.')[1]
    }


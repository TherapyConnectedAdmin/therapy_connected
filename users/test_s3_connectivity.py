import boto3
import os
from dotenv import load_dotenv

load_dotenv()

bucket = os.getenv('AWS_STORAGE_BUCKET_NAME')
region = os.getenv('AWS_S3_REGION_NAME', 'us-east-1')
access_key = os.getenv('AWS_ACCESS_KEY_ID')
secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')

s3 = boto3.client('s3', region_name=region, aws_access_key_id=access_key, aws_secret_access_key=secret_key)

def test_connectivity():
    try:
        response = s3.list_objects_v2(Bucket=bucket, MaxKeys=1)
        print(f"Successfully connected to bucket '{bucket}'. Contents:")
        for obj in response.get('Contents', []):
            print(f"- {obj['Key']}")
        if not response.get('Contents'):
            print("Bucket is empty but accessible.")
    except Exception as e:
        print(f"Error connecting to bucket: {e}")

if __name__ == "__main__":
    test_connectivity()

import json
import pymysql

def lambda_handler(event, context):
    if event['httpMethod'] == 'POST' and event['path'] == '/v0igir01':
        output = {
            'message1': 'CSE 335 Lambda',
            'message2': 'Group Project',
            'laugh': 'web inteface'
        }
        return {
            'statusCode': 200,
            'body': json.dumps('output')
        }
    else:
        errorData = {
            'error': 'PATH not found'
        }
        return {
            'statusCode': 404,
            'body': json.dumps(errorData)
        }
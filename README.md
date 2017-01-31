# CTFd-S3-plugin
Plugin that converts CTFd file uploads and deletions to Amazon S3 calls

## Installation

1. To install clone this repository to the [CTFd/plugins](https://github.com/isislab/CTFd/tree/master/CTFd/plugins) folder.
2. Edit [CTFd/config.py](https://github.com/isislab/CTFd/blob/master/CTFd/config.py) and add the following entries:
  * ACCESS_KEY_ID
  * SECRET_ACCESS_KEY
  * BUCKET 

`ACCESS_KEY_ID` is your AWS Access Key. If you do not provide this, the plugin will try to use an IAM role or credentials file.

`SECRET_ACCESS_KEY` is your AWS Secret Key. If you do not provide this, the plugin will try to use an IAM role or credentials file.

`BUCKET` is the name of your Amazon S3 bucket. 

## Note

This plugin will not yet backfill any files you've uploaded. If you install the plugin after you've uploaded files, you will need to upload your current challenge files to S3. 

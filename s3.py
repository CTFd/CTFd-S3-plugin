from flask import request, redirect, abort, jsonify, url_for
from CTFd.models import db, Solves, Challenges, WrongKeys, Keys, Tags, Files

from CTFd import utils
import os
import boto3
import hashlib
import string
from werkzeug.utils import secure_filename


def clean_filename(c):
    if c in string.ascii_letters + string.digits + '-' + '_' + '.':
        return True


def get_s3_conn(app):
    access_key_id = utils.get_config('ACCESS_KEY_ID')
    secret_access_key = utils.get_config('SECRET_ACCESS_KEY')
    if access_key_id and secret_access_key:
        client = boto3.client(
            's3',
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key
        )
        bucket = utils.get_config('BUCKET')
        return client, bucket
    else:
        client = boto3.client('s3')
        bucket = utils.get_config('BUCKET')
        return client, bucket


def load(app):
    def upload_file(file, chalid):
        s3, bucket = get_s3_conn(app)

        filename = filter(clean_filename, secure_filename(file.filename).replace(' ', '_'))
        if len(filename) <= 0:
            return False

        md5hash = hashlib.md5(os.urandom(64)).hexdigest()

        key = md5hash + '/' + filename
        print file
        print bucket, key
        s3.upload_fileobj(file, bucket, key)

        db_f = Files(chalid, key)
        db.session.add(db_f)
        db.session.commit()
        return True

    def delete_file(filename):
        s3, bucket = get_s3_conn(app)
        f = Files.query.filter_by(id=filename).first_or_404()
        key = f.location
        s3.delete_object(Bucket=bucket, Key=key)
        db.session.delete(f)
        db.session.commit()
        return True

    def file_handler(path):
        f = Files.query.filter_by(location=path).first_or_404()
        chal = Challenges.query.filter_by(id=f.chal).first()

        s3, bucket = get_s3_conn(app)
        if utils.is_admin():
            key = f.location
            url = s3.generate_presigned_url('get_object', Params = {
                'Bucket': bucket,
                'Key': key, })
            return redirect(url)

        if utils.user_can_view_challenges():
            if not utils.ctftime():
                if not utils.view_after_ctf():
                    abort(403)

            if chal.hidden:
                abort(403)

            key = f.location
            url = s3.generate_presigned_url('get_object', Params = {
                'Bucket': bucket,
                'Key': key, })
            return redirect(url)
        else:
            return redirect(url_for('auth.login'))

    utils.upload_file = upload_file
    utils.delete_file = delete_file
    app.view_functions['views.file_handler'] = file_handler
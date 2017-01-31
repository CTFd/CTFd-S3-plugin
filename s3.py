from flask import request, redirect, abort, jsonify, url_for
from CTFd.utils import is_admin, ctftime, user_can_view_challenges, view_after_ctf, admins_only
from CTFd.models import db, Solves, Challenges, WrongKeys, Keys, Tags, Files

import os
import boto
import hashlib
import string
from werkzeug.utils import secure_filename
from boto.s3.key import Key


def clean_filename(c):
    if c in string.ascii_letters + string.digits + '-' + '_' + '.':
        return True


def get_s3_conn():
    if app.config.get('ACCESS_KEY_ID') and app.config.get('SECRET_ACCESS_KEY'):
        return boto.connect_s3(app.config.get('ACCESS_KEY_ID'), app.config.get('SECRET_ACCESS_KEY'))
    else:
        return boto.connect_s3()


def load(app):
    def file_handler(path):
        f = Files.query.filter_by(location=path).first_or_404()
        chal = Challenges.query.filter_by(id=f.chal).first()

        if is_admin():
            s3 = get_s3_conn()
            bucket_name = app.config.get('BUCKET')
            bucket = s3.get_bucket(bucket_name)
            k = Key(bucket)
            k.key = f.location
            url = k.generate_url(expires_in=600, query_auth=True)
            return redirect(url)

        if user_can_view_challenges():
            if not ctftime():
                if not view_after_ctf():
                    abort(403)

            if chal.hidden:
                abort(403)

            s3 = get_s3_conn()
            bucket_name = app.config.get('BUCKET')
            bucket = s3.get_bucket(bucket_name)
            k = Key(bucket)
            k.key = f.location
            url = k.generate_url(expires_in=600, query_auth=True)
            return redirect(url)
        else:
            return redirect(url_for('auth.login'))

    @admins_only
    def admin_files(chalid):
        if request.method == 'GET':
            files = Files.query.filter_by(chal=chalid).all()
            json_data = {'files': []}
            for x in files:
                json_data['files'].append({'id': x.id, 'file': x.location})
            return jsonify(json_data)
        if request.method == 'POST':
            s3 = get_s3_conn()
            bucket_name = app.config.get('BUCKET')
            bucket = s3.get_bucket(bucket_name)
            k = Key(bucket)
            if request.form['method'] == "delete":
                f = Files.query.filter_by(id=request.form['file']).first_or_404()
                k.key = f.location
                bucket.delete_key(k)
                db.session.delete(f)
                db.session.commit()
                db.session.close()
                return "1"
            elif request.form['method'] == "upload":
                files = request.files.getlist('files[]')

                for f in files:
                    filename = filter(clean_filename, secure_filename(f.filename).replace(' ', '_'))

                    if len(filename) <= 0:
                        continue

                    md5hash = hashlib.md5(os.urandom(64)).hexdigest()

                    file_contents = f.read()
                    k.key = md5hash + '/' + filename
                    k.set_contents_from_string(file_contents)

                    db_f = Files(chalid, md5hash + '/' + filename)
                    db.session.add(db_f)

                db.session.commit()
                db.session.close()
                return redirect(url_for('admin.admin_chals'))

    @admins_only
    def admin_create_chal():
        files = request.files.getlist('files[]')

        ## TODO: Expand to support multiple flags
        flags = [{'flag': request.form['key'], 'type': int(request.form['key_type[0]'])}]
        chal = Challenges(request.form['name'], request.form['desc'], request.form['value'], request.form['category'], flags)
        if 'hidden' in request.form:
            chal.hidden = True
        else:
            chal.hidden = False
        db.session.add(chal)
        db.session.commit()

        s3 = get_s3_conn()
        bucket_name = app.config.get('BUCKET')
        bucket = s3.get_bucket(bucket_name)
        k = Key(bucket)

        for f in files:
            filename = filter(clean_filename, secure_filename(f.filename).replace(' ', '_'))

            if len(filename) <= 0:
                continue

            md5hash = hashlib.md5(os.urandom(64)).hexdigest()

            file_contents = f.read()
            k.key = md5hash + '/' + filename
            k.set_contents_from_string(file_contents)

            db_f = Files(chal.id, md5hash + '/' + filename)
            db.session.add(db_f)
        db.session.commit()
        db.session.close()
        return redirect(url_for('admin.admin_chals'))

    @admins_only
    def admin_delete_chal():
        challenge = Challenges.query.filter_by(id=request.form['id']).first()
        if challenge:
            WrongKeys.query.filter_by(chalid=challenge.id).delete()
            Solves.query.filter_by(chalid=challenge.id).delete()
            Keys.query.filter_by(chal=challenge.id).delete()
            files = Files.query.filter_by(chal=challenge.id).all()
            Files.query.filter_by(chal=challenge.id).delete()
            s3 = get_s3_conn()
            bucket_name = app.config.get('BUCKET')
            bucket = s3.get_bucket(bucket_name)
            k = Key(bucket)
            for file in files:
                k.key = file.location
                bucket.delete_key(k)
            Tags.query.filter_by(chal=challenge.id).delete()
            Challenges.query.filter_by(id=challenge.id).delete()
            db.session.commit()
            db.session.close()
        return '1'

    app.view_functions['views.file_handler'] = file_handler
    app.view_functions['admin.admin_create_chal'] = admin_create_chal
    app.view_functions['admin.admin_files'] = admin_files
    app.view_functions['admin.admin_delete_chal'] = admin_delete_chal
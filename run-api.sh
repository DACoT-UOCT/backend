mail_creation_recipients=$MAIL_CREATE_RECIPIENTS mail_enabled=$MAIL_ENABLED mail_server=$MAIL_SERVER mail_port=$MAIL_PORT mail_user=$MAIL_USER mail_pass=$MAIL_PASS mail_tls=$MAIL_TLS mail_ssl=$MAIL_SSL mongo_uri="$MONGO_URL" uvicorn --host 0.0.0.0 --port 8080 app.main:app

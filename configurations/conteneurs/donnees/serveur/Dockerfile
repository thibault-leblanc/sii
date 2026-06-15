FROM alpine:latest

RUN apk add --no-cache vsftpd

# On injecte la configuration FTP directement ici pour esquiver les bugs Windows
RUN echo '#!/bin/sh' > /start.sh && \
    echo 'FTP_USER=${FTP_USER:-admin}' >> /start.sh && \
    echo 'FTP_PASS=${FTP_PASS:-admin}' >> /start.sh && \
    echo 'adduser -D -h /partage $FTP_USER' >> /start.sh && \
    echo 'echo "$FTP_USER:$FTP_PASS" | chpasswd' >> /start.sh && \
    echo 'chown -R $FTP_USER:$FTP_USER /partage' >> /start.sh && \
    echo 'echo "listen=YES" > /etc/vsftpd/vsftpd.conf' >> /start.sh && \
    echo 'echo "local_enable=YES" >> /etc/vsftpd/vsftpd.conf' >> /start.sh && \
    echo 'echo "write_enable=YES" >> /etc/vsftpd/vsftpd.conf' >> /start.sh && \
    echo 'echo "seccomp_sandbox=NO" >> /etc/vsftpd/vsftpd.conf' >> /start.sh && \
    echo 'echo "pasv_enable=YES" >> /etc/vsftpd/vsftpd.conf' >> /start.sh && \
    echo 'echo "pasv_min_port=21000" >> /etc/vsftpd/vsftpd.conf' >> /start.sh && \
    echo 'echo "pasv_max_port=21010" >> /etc/vsftpd/vsftpd.conf' >> /start.sh && \
    echo 'exec vsftpd /etc/vsftpd/vsftpd.conf' >> /start.sh && \
    chmod +x /start.sh

ENTRYPOINT ["/start.sh"]
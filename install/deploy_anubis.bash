# Anubis: update from GitHub and restart
cd /var/www/apps/Anubis
sudo -u nginx git pull
systemctl restart anubis
semanage fcontext -a -t httpd_sys_rw_content_t /var/www/apps/Anubis/site/nginx.sock
restorecon -R /var/www/apps/Anubis

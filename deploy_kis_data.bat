scp -i "id_rsa" -o StrictHostKeyChecking=no "kis_data.py" ubuntu@141.148.172.12:/home/ubuntu/kis-auto-trading/kis_data.py
ssh -i "id_rsa" -o StrictHostKeyChecking=no ubuntu@141.148.172.12 "sudo systemctl restart kis-trading"

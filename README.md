# Functional
- login (email verification feature)
- send invites based on keyword position
- check/accept invites
- send bulk messages to all users or specific it is connected with
- comments on posts
- autoreply message (new connections within 24 hours)

## IMPORTANT DATA
App on starting run some base tests
So before first app running be sure:
- initialize db
- your system support cron

### Tasks 
When you use `/send_invites` endpoint, app generate background task, 
you can check is task completed using `/logs` endpoint (need send only `task_id` param).
Task ID and it's result stored in tasks endpoint. You can clean this table (but old tasks info will be not available).

### Structure
`api/` - contains flask and other app parts code
`linkedin_api/` - contains only linkedin (not official) specific code
`logs/` - app logs
`tests/` - app tests
`tools/` - some helper scripts (for example fore_login.py, this script use multiple proxies and tries cause location change event - linkedin will ask pin)
`conf/` - some configurations samples
`.env` - app secrets
`library.db` - app database

# Flask REST API linkedinbot

## Install guide

##### Clone the repo and creat secrets

```bash
git clone <URL>
cd linked_bot
cp env.sample .env # need modify API_KEY and other values inside this file!!!
```

##### Create and activate the virtualenv
```bash
pip3 install --upgrade pip
python3 -m venv ./venv #  or python36 -m venv ./venv
 . ./venv/bin/activate # or . ./venv/bin/activate.fish
pip3 install -r requirements.txt
mkdir logs
cp env.sample .env # you need check and edit this file!
$ sqlite3 library.db < library-schema.sql # only first time!
# Run as limited user!
$ chown -R linkedin:linkedin /home/linkedin/*
$ su linkedin
$ cd ...path_to_app...

```

##### Install Dependencies
```bash
# install python 3, pip before
sudo yum install nginx
pip3 install supervisor superlance
supervisord --version

# create service file
sudo cp conf/supervisor_linkedin.conf /etc/supervisor_linkedin.conf
mkdir /var/log/supervisor/
chown linkedin:linkedin /var/log/supervisor/
nano -w /usr/lib/systemd/system/supervisord.service
```
[Unit]
Description=supervisord - Supervisor process control system for UNIX
Documentation=http://supervisord.org
After=network.target

[Service]
Type=forking
ExecStart=/usr/local/bin/supervisord -c /etc/supervisor_linkedin.conf
ExecReload=/usr/local/bin/supervisorctl reload
ExecStop=/usr/local/bin/supervisorctl shutdown
User=linkedin

[Install]
WantedBy=multi-user.target
```


##### Open some ports
firewall-cmd --get-active-zones
firewall-cmd --zone=public --add-port=48000/tcp --permanent
firewall-cmd --reload


```
##### Configure Supervisor
```bash
# you need go to current project path

supervisorctl reread
supervisorctl add fatalmailbatch
supervisorctl start fatalmailbatch

sudo supervisorctl reread
sudo supervisorctl status

# start service 
sudo systemctl start supervisord
# view service status:
sudo systemctl status supervisord
# auto start service on system startup:
sudo systemctl enable supervisord
# optionall reboot...
```
##### Configure nginix
```bash
# you need check servername!
sudo cp conf/nginx_linkedin.conf /etc/nginx/nginx.conf
sudo systemctl start nginx
sudo systemctl status nginx
sudo systemctl enable nginx
```


Also need install python3

##### Run the app simple method (maybe better use gunicorn here)

You need run app using supervisord (check conf/supervisor_linkedin.conf and setup above).
You can also run app locally
activate venv, install requirements.txt and run app 
using `python3 run_app.py &` or `python36 run_app.py &`


##### If need open port -
https://stackoverflow.com/questions/24729024/open-firewall-port-on-centos-7
or other guide

#### Notes
Todo: convert requests to curl format

logs is placed in linkedin_app.log

If you use imap lib and gmail, need configure imap
https://support.google.com/accounts/answer/6010255?hl=en 

Success login example
https://yadi.sk/d/e0T4TFI9CKTCIA

### API methods:
All app endpoints can work with post requests, for each request need send login, pass, proxy and secret key header  
http://45.76.4.112:48000 - can be yours!
Curl examples - you can use some tool to convert curl into other format (check postman app or online service)

### `/login`  
This endpoint remove cache and force login.
By default app cache cookies into database, to start session.
Cache time is 2 hours. Configurable - client.py LOGIN_DELAY

```bash
curl -X POST -H "X-Api-Key: H#nImhPt]aM%T_t7%r5Tt4uV7F-pD*p<)BY/[FbtevAFLlh!F*V_Z" \
-d 'username=libelaft%40aol.com&password=diDZ3y1hT&proxy=138.128.19.56%3A9583%3AtKHzyq%3AgaNfx9' \
'http://45.76.4.112:48000/login' 
```

Login can ask code! (when you change proxy location)

You need send key!
### `/send_key`
This endpoint send key to authorize user (captcha is not supported!)
```bash
curl -X POST -H "X-Api-Key: H#nImhPt]aM%T_t7%r5Tt4uV7F-pD*p<)BY/[FbtevAFLlh!F*V_Z" \
-d 'username=libelaft%40aol.com&password=diDZ3y1hT&proxy=138.128.19.56%3A9583%3AtKHzyq%3AgaNfx9&key=123456' \
'http://45.76.4.112:48000/send_key' 
```


### `/send_invites`  
```bash
curl -X POST -H "X-Api-Key: H#nImhPt]aM%T_t7%r5Tt4uV7F-pD*p<)BY/[FbtevAFLlh!F*V_Z" \
-d 'username=libelaft%40aol.com&password=diDZ3y1hT&proxy=138.128.19.56%3A9583%3AtKHzyq%3AgaNfx9&keywords=developer&message=Hello+{firstname}!&max_results=200' \
'http://45.76.4.112:48000/send_invites' 
```
**WARNING** - some users cannot connect with you, search result can be low for some keywords!

keywords <str> - keywords, comma seperated, search by keywords and send invite,
app can send invite, but if connection is not possible (not possible for current user)
invition can not work
message - optional param, send invite with some message, you can use {firstname} and {lastname} variables in this param
send_delay (number) - optional param, send delay in seconds (for example, 1 hour is 3600 seconds)
check_previous_invites (yes or no) optional param, check previous invites (old invites stored in DB, for each user!). Default yes.

#### optional params
connection_of <str> - urn id of a profile. Only people connected to this profile are returned
network_depth <str> - the network depth to search within. One of {F, S, or O} (first, second and third+ respectively)
regions <list> - list of Linkedin region ids, use multiple regions[] as values (regions[]=1...regions[]=10)
industries <list> - list of Linkedin industry ids, use multiple industries[] as values
max_results <int> - maximum search result

### `/send_messages`
```bash
 curl -X POST  -H "X-Api-Key: H#nImhPt]aM%T_t7%r5Tt4uV7F-pD*p<)BY/[FbtevAFLlh!F*V_Z" \
 -d 'username=libelaft%40aol.com&password=diDZ3y1hT&proxy=138.128.19.56%3A9583%3AtKHzyq%3AgaNfx9&message=ty&max_results=200' \
 'http://45.76.4.112:48000/send_messages'
```
if some messages thread already exist (old conversation), it use old thread
else  endpoint create thread with user/users and send some message (once)

message <str> - some message
#### optional params
max_results <int> - your maximum connections, don't add this param if you want send messages to all connections
send_message_interval <int> - optional timeout between sending messages, default 4 seconds

If you want send message to multiple or single users 
pass signle or comma separated string with public_id/public_ids or urn_id, urn_ids 

Examples:

public_ids <str> optional like  `michael-brian-3b168a184`   
urn_ids <str> optional like  `ACoAACuG1bUB2BZR42jWc_3RKmb6bdHKaRMI9CA`   

public_ids <str> optional like  `michael-brian-3b168a184,lance-s-harting-46656267`   
urn_ids <str> optional like  `ACoAACuG1bUB2BZR42jWc_3RKmb6bdHKaRMI9CA,ACoAAA4kYg4BCK-m1512fjDt2QZC_VH_clZ5QFY`

If you send multiple messages, check  messages_sent result, if you pass 2 public_ids/urn_ids messages_sent must be 2 

### `/whoami`
WARNING `cronjob_create` here not working (not needed?)!

optional params max_results - here your maximum connections (default 40), omit this to check all connections
```bash
 curl -X POST  -H "X-Api-Key: H#nImhPt]aM%T_t7%r5Tt4uV7F-pD*p<)BY/[FbtevAFLlh!F*V_Z" \
 -d 'username=libelaft%40aol.com&password=diDZ3y1hT&proxy=138.128.19.56%3A9583%3AtKHzyq%3AgaNfx9&max_results=20' \
 'http://45.76.4.112:48000/whoami'
```
Check user info and their connection
Return examples:
```json
{
   "user_info":{
      "firstName":"Xx",
      "lastName":"Xx",
      "occupation":"",
      "publicIdentifier":"xxx",
      "picture":[
         {
            "url":"https://media.licdn.com/dms/image/C5103AQH7r6SpVsGZtA/profile-displayphoto-shrink_100_100/0?e=1556755200&v=beta&t=3oKZ1m3YC-53rVmXUHE6XKcZqMBE175uTKd2KiqjrbE",
            "dimensions":"100x100",
            "expiresAt":1556755200000
         },
         {
            "url":"https://media.licdn.com/dms/image/C5103AQH7r6SpVsGZtA/profile-displayphoto-shrink_200_200/0?e=1556755200&v=beta&t=4Txx4opmoz1ifLl8qCZxhknlGp23IK4qJKddaOCwMmg",
            "dimensions":"200x200",
            "expiresAt":1556755200000
         },
         {
            "url":"https://media.licdn.com/dms/image/C5103AQH7r6SpVsGZtA/profile-displayphoto-shrink_400_400/0?e=1556755200&v=beta&t=7l8PicBBK0J4ulzMniBcUBpn8h0vqXfEDUDsPQzY-d0",
            "dimensions":"400x400",
            "expiresAt":1556755200000
         },
         {
            "url":"https://media.licdn.com/dms/image/C5103AQH7r6SpVsGZtA/profile-displayphoto-shrink_800_800/0?e=1556755200&v=beta&t=LHJnHv5J2Zut6ze_Z8pdaIDrNevYThwwAb9-R-mIskk",
            "dimensions":"800x800",
            "expiresAt":1556755200000
         }
      ]
   },
   "user_connections":[
      {
         "firstName":"Ekaterina",
         "lastName":"Chmуr",
         "occupation":"Looking for Strong Junior Python and Middle Python Dev",
         "publicIdentifier":"ekaterina-chmуr-2044b9158",
         "picture":[
            {
               "url":"https://media.licdn.com/dms/image/C5603AQFk-v176hifWw/profile-displayphoto-shrink_100_100/0?e=1556755200&v=beta&t=z9xNbnLDEKhM9DYRkplFcsYPZuwXbGndDSfcG3aOEHU",
               "dimensions":"100x100",
               "expiresAt":1556755200000
            },
            {
               "url":"https://media.licdn.com/dms/image/C5603AQFk-v176hifWw/profile-displayphoto-shrink_200_200/0?e=1556755200&v=beta&t=2-fvi_8QaK_kEOVsoodjgnt-d5rL-TutscI5mNbE0Bo",
               "dimensions":"200x200",
               "expiresAt":1556755200000
            },
            {
               "url":"https://media.licdn.com/dms/image/C5603AQFk-v176hifWw/profile-displayphoto-shrink_400_400/0?e=1556755200&v=beta&t=4eeuE08YTglY5TbxFVjYNhU4R1-JuX3d3HmpF9LJQCc",
               "dimensions":"400x400",
               "expiresAt":1556755200000
            },
            {
               "url":"https://media.licdn.com/dms/image/C5603AQFk-v176hifWw/profile-displayphoto-shrink_800_800/0?e=1556755200&v=beta&t=jmzYgsY-yv1GWjYDrHXER7YWqLq5JVUdCuS_jkssqhg",
               "dimensions":"800x800",
               "expiresAt":1556755200000
            }
         ]
      },
      {
         "firstName":"Maksym ",
         "lastName":"Parats",
         "occupation":"Data Science Engineering / Machine Learning Modeling / Python dev",
         "publicIdentifier":"maksym-parats-65676a139",
         "picture":[
            {
               "url":"https://media.licdn.com/dms/image/C4D03AQGXnG3SsYpnDg/profile-displayphoto-shrink_100_100/0?e=1556755200&v=beta&t=PeMy10TXR84kGOa_0TD0AuVdGiGpqUDLGz-26b_3ONo",
               "dimensions":"100x100",
               "expiresAt":1556755200000
            },
            {
               "url":"https://media.licdn.com/dms/image/C4D03AQGXnG3SsYpnDg/profile-displayphoto-shrink_200_200/0?e=1556755200&v=beta&t=acZSaovjXa7dFh6EMSm0KyBgT0Ql9hr9kN2HKZofCjs",
               "dimensions":"200x200",
               "expiresAt":1556755200000
            },
            {
               "url":"https://media.licdn.com/dms/image/C4D03AQGXnG3SsYpnDg/profile-displayphoto-shrink_400_400/0?e=1556755200&v=beta&t=TzuZ9QNxHyICGixhzl_8SJTrBOK3XQ7ttg7q9BZawOY",
               "dimensions":"400x400",
               "expiresAt":1556755200000
            },
            {
               "url":"https://media.licdn.com/dms/image/C4D03AQGXnG3SsYpnDg/profile-displayphoto-shrink_800_800/0?e=1556755200&v=beta&t=DOf-VsDT5AFVY8ieGZAVxwUNTQSaGM8vd-mdrOdlrRQ",
               "dimensions":"800x800",
               "expiresAt":1556755200000
            }
         ]
      },
      {
         "firstName":"Natali",
         "lastName":"Rybaltovskaya",
         "occupation":"Looking for DB dev and Python dev",
         "publicIdentifier":"natali-rybaltovskaya-52635767",
         "picture":[
            {
               "url":"https://media.licdn.com/dms/image/C5603AQFzm250MKUTXw/profile-displayphoto-shrink_100_100/0?e=1556755200&v=beta&t=al7b9JERawiw8Zi5ARpZRoQWWQ2N80OVMYnxvoO1Kyw",
               "dimensions":"100x100",
               "expiresAt":1556755200000
            },
            {
               "url":"https://media.licdn.com/dms/image/C5603AQFzm250MKUTXw/profile-displayphoto-shrink_200_200/0?e=1556755200&v=beta&t=jnowm4VNvfzuGGQ3rFIxaRBzQFMRi3p3pSc_WJUkgZ8",
               "dimensions":"200x200",
               "expiresAt":1556755200000
            },
            {
               "url":"https://media.licdn.com/dms/image/C5603AQFzm250MKUTXw/profile-displayphoto-shrink_400_400/0?e=1556755200&v=beta&t=uz9ftwuGVPuu22E9nJoI3lnMaQbEN_Kn7nSEoiS8huk",
               "dimensions":"400x400",
               "expiresAt":1556755200000
            },
            {
               "url":"https://media.licdn.com/dms/image/C5603AQFzm250MKUTXw/profile-displayphoto-shrink_800_800/0?e=1556755200&v=beta&t=Lm9Luw6izScFYi0CYeOl94N0ENRKX3WIaNjrDO7Po6I",
               "dimensions":"800x800",
               "expiresAt":1556755200000
            }
         ]
      },
      {
         "firstName":"Alesia",
         "lastName":"Tryfanava",
         "occupation":"Looking for Senior/Lead Python dev",
         "publicIdentifier":"alesyatrifonova",
         "picture":[
            {
               "url":"https://media.licdn.com/dms/image/C5603AQEoI2IaDe0T8A/profile-displayphoto-shrink_100_100/0?e=1556755200&v=beta&t=BWjKlc6VkeeamXSGLiPCl3wKidjOygT7JbXXgg6N1fA",
               "dimensions":"100x100",
               "expiresAt":1556755200000
            },
            {
               "url":"https://media.licdn.com/dms/image/C5603AQEoI2IaDe0T8A/profile-displayphoto-shrink_200_200/0?e=1556755200&v=beta&t=WkQ9sB5oSkkPV2Spd54J62dWsF6TyHq0WicDmCKbEdQ",
               "dimensions":"200x200",
               "expiresAt":1556755200000
            },
            {
               "url":"https://media.licdn.com/dms/image/C5603AQEoI2IaDe0T8A/profile-displayphoto-shrink_400_400/0?e=1556755200&v=beta&t=XjMPT_Dofxwe4KBTbTSF_IDb-knJi5m4l4snuRtwPsc",
               "dimensions":"400x400",
               "expiresAt":1556755200000
            },
            {
               "url":"https://media.licdn.com/dms/image/C5603AQEoI2IaDe0T8A/profile-displayphoto-shrink_800_800/0?e=1556755200&v=beta&t=IdYfcz6PeedPYRPS2pLV3qIodSY66qmZibNOBUPZYas",
               "dimensions":"800x800",
               "expiresAt":1556755200000
            }
         ]
      },
      {
         "firstName":"Sunil",
         "lastName":"Ch",
         "occupation":"PHP & WordPress Developer",
         "publicIdentifier":"sunildesigner",
         "picture":[
            {
               "url":"https://media.licdn.com/dms/image/C4D03AQFHCGlqWNGiAg/profile-displayphoto-shrink_100_100/0?e=1556755200&v=beta&t=q0xMm-xFUF6l-RD9v2Mx7Uo6vNX6Aris9cw-rxcGrjk",
               "dimensions":"100x100",
               "expiresAt":1556755200000
            },
            {
               "url":"https://media.licdn.com/dms/image/C4D03AQFHCGlqWNGiAg/profile-displayphoto-shrink_200_200/0?e=1556755200&v=beta&t=nyLYKujxxJ2u6zTyg6k-JDsN41A08IEuFnzmMs8SgDI",
               "dimensions":"200x200",
               "expiresAt":1556755200000
            },
            {
               "url":"https://media.licdn.com/dms/image/C4D03AQFHCGlqWNGiAg/profile-displayphoto-shrink_400_400/0?e=1556755200&v=beta&t=ylvP5RcfJ2cQAOKSbH83lWiZbtsev29ZReal7uWsy6U",
               "dimensions":"400x400",
               "expiresAt":1556755200000
            },
            {
               "url":"https://media.licdn.com/dms/image/C4D03AQFHCGlqWNGiAg/profile-displayphoto-shrink_800_800/0?e=1556755200&v=beta&t=2TTR5YJi7LAP4o9yDsA1XH5F-A2eKstje_7PbZdlwko",
               "dimensions":"800x800",
               "expiresAt":1556755200000
            }
         ]
      }
   ],
   "user_connections_count":5,
   "api_is_working":true,
   "success":true
}
```

message <str> - some message
#### optional params
max_results <int> - your maximum connections
send_message_interval <int> - optional timeout between sending messages, default 4 seconds
    

    
### `/accept_invites`  
```bash
curl -X POST -H "X-Api-Key: H#nImhPt]aM%T_t7%r5Tt4uV7F-pD*p<)BY/[FbtevAFLlh!F*V_Z" \
-d 'username=libelaft%40aol.com&password=diDZ3y1hT&proxy=138.128.19.56%3A9583%3AtKHzyq%3AgaNfx9' \
'http://45.76.4.112:48000/accept_invites'
```
this endpoint check inbox with ALL invites and accept them
using cron you can send this response each N hours

### `/post_comment`
```bash
 curl -X POST -H "X-Api-Key: H#nImhPt]aM%T_t7%r5Tt4uV7F-pD*p<)BY/[FbtevAFLlh!F*V_Z" \
-d 'username=libelaft%40aol.com&password=diDZ3y1hT&proxy=138.128.19.56%3A9583%3AtKHzyq%3AgaNfx9&message=very+interesting!&post_url=https%3A%2F%2Fwww.linkedin.com%2Ffeed%2Fupdate%2Furn%3Ali%3Aactivity%3A6492467023828779008%2F' \
'http://45.76.4.112:48000/post_messages' 
```

Post messages on some post, you just need pass url with post, like
`https://www.linkedin.com/feed/update/urn:li:activity:6488708042790662145` (you can get this url on linkedin page)
and message.

App will post 1 comment

### `/get_user_info`
```bash
curl -X POST -H "X-Api-Key: H#nImhPt]aM%T_t7%r5Tt4uV7F-pD*p<)BY/[FbtevAFLlh!F*V_Z" \
-d 'username=libelaft%40aol.com&password=diDZ3y1hT&proxy=138.128.19.56%3A9583%3AtKHzyq%3AgaNfx9&urn_id=ACoAAA4kYg4BCK-m1512fjDt2QZC_VH_clZ5QFY' \
'http://45.76.4.112:48000/get_user_info' 
```
this endpoint return additional info for specific `urn_id` or `public_id`

You need send to this endpoint user, password, proxy and (urn_id or public_id)

urn_id example: ACoAACprUIwBtzNv4F9AflNgR-Wgfm6tZ-OGx88
public_id example: jessica-mitchell-69040917a

### `/send_key`  
```bash
curl -X POST -H "X-Api-Key: H#nImhPt]aM%T_t7%r5Tt4uV7F-pD*p<)BY/[FbtevAFLlh!F*V_Z" \
-d 'username=exactnass@aol.com&password=GBk7ypN4b&proxy=138.128.19.56:9583:tKHzyq:gaNfx9&key=123456' \
'http://45.76.4.112:48000/post_messages' 
```

### `/regions`
This endpoint return regions codes, which you can use with `send_invites` api endpoint


### `/logs`
```bash
curl -X POST -H 'x-api-key: H#nImhPt]aM%T_t7%r5Tt4uV7F-pD*p<)BY/[FbtevAFLlh!F*V_Z' \
-d 'username=i@inomoz.ru&max_results=656' \
'http://45.76.4.112:5000/logs'

curl -X POST -H 'x-api-key: H#nImhPt]aM%T_t7%r5Tt4uV7F-pD*p<)BY/[FbtevAFLlh!F*V_Z' \
-d 'task_id=1555075133_becdb96c-7313-4fa2-be88-9484dc68c903_i@inomoz.ru' \
'http://45.76.4.112:5000/logs'

```
Endpoint to get logs!
To get task result need send `task_id` param with string

You need pass username (email) to get user blacklist.
max_results - optional param, default is 200. Limit log lines.
order_keyword (ASC, DESC) - optional param, sort lines by TimeStamp ascending or descending . Default is DESC
 
Logs also return some info from user and codes tables

### Crontab params
Each endpoint (except logs/special endpoints) accept 2 special params:
`cronjob_create` <str> - optional param, yes/no. Use it to generate crontab job.
`setall_string` <str> - optional param, here need pass crontab expression (working only if create_crontab=yes)  
Check https://crontab.guru for `setall_string` examples.

If you pass `cronjob_create` and `setall_string` endpoint return specific response data:
```json
"job_id": "1550063272_e3a6ef27-fdc3-4dff-afa2-6c290ef821fe",
"job_frequency": "At 14:15, .....", 
"job_command": "curl -X POST -H \"Content-Type: application/json\" -H \"X-Api-Key: H#nImhPt]aM%T_t7%r5Tt4uV7F-pD*p<)BY/[FbtevAFLlh!F*V_Z\" 'http://45.76.4.112:48000/post_messages?username=i%40inomoz.ru&proxy=138.128.19.83%3A9759%3AfpS4Nb%3ADFg2Gm&password=&keywords=wordpress+developer&send_delay=2&check_previous_invites=y&message=%3D%29&max_results=1&send_message_interval=10&post_url=https%3A%2F%2Fwww.linkedin.com%2Ffeed%2Fupdate%2Furn%3Ali%3AugcPost%3A6494548936274116608%2F&section=invite&setall_string=15+14+1+%2A+%2A&job_id=1550062275_4c43d656-7642-4522-a541-dc4de2b98b59'",
"cron_generated": true}
```

`cron_generated: true` means new cronjob created! (written to crontab file).
you can use `job_id` later to check or delete this job.

#### Crontab `/check_job` endpoint
You can pass here job_id (check info about this above)
and receive some job info.

For example:

```bash
curl -X POST -H "X-Api-Key: H#nImhPt]aM%T_t7%r5Tt4uV7F-pD*p<)BY/[FbtevAFLlh!F*V_Z" \
-d 'job_id=1550062846_81510130-360d-4f74-a585-ba62a3eb0406' \
'http://45.76.4.112:48000/check_job'
```

result  
```json
{"1550062846_81510130-360d-4f74-a585-ba62a3eb0406": "curl -X POST -H \"Content-Type: application/json\" -H \"X-Api-Key: H#nImhPt]aM%T_t7%r5Tt4uV7F-pD*p<)BY/[FbtevAFLlh!F*V_Z\" 'http://45.76.4.112:48000/post_messages?username=i%40inomoz.ru&proxy=138.128.19.83%3A9759%3AfpS4Nb%3ADFg2Gm&password=&keywords=wordpress+developer&send_delay=2&check_previous_invites=y&message=%3D%29&max_results=1&send_message_interval=10&post_url=https%3A%2F%2Fwww.linkedin.com%2Ffeed%2Fupdate%2Furn%3Ali%3AugcPost%3A6494548936274116608%2F&section=invite&setall_string=15+14+1+%2A+%2A&job_id=1550062275_4c43d656-7642-4522-a541-dc4de2b98b59'",
"success": true,}
```

#### Crontab `/delete_job` endpoint
You can pass here job_id (check info about this above)
and delete some job.

For example:
```bash
curl -X POST -H "X-Api-Key: H#nImhPt]aM%T_t7%r5Tt4uV7F-pD*p<)BY/[FbtevAFLlh!F*V_Z" \
-d 'job_id=1550062846_81510130-360d-4f74-a585-ba62a3eb0406'
'http://45.76.4.112:48000/delete_job'
```

result  
`{"job_deleted": true, "success": true}`

Here no endpoints to delete all cron-jobs, if need delete all cron-jobs do it manually (crontab -e).


#### Crontab `/delete_user` endpoint
You can pass here user email and delete it from DB

For example:
```bash
curl -X POST  -H "X-Api-Key: H#nImhPt]aM%T_t7%r5Tt4uV7F-pD*p<)BY/[FbtevAFLlh!F*V_Z" \
-d 'delete_user=example@example.com' \
'http://45.76.4.112:48000/'
```

result  
```json
{
 "success": true,                 # successfly deleted user or just skipped
 "logs_not_exist": true,          # no data with this user in logs table
 "user_not_exist": true,          # no data with this user in user table
 "user_codes_not_exist": true,    # no data with this user in codes table
 "cronjobs_removed": 0,           # removed cronjobs with this user
 "user": "example@example.com" # this is deleted user
}
```


### ADDITIONAL
#### Useful sources
https://linkedin.api-docs.io/

Quick Sync  
`rsync -avzX  --exclude=venv --exclude=.idea --exclude=tmp --exclude=library.db ./ root@45.76.4.112:/home/linkedin/`

gracefully restarts workers if you change any of your python code and want to restart the application  
`killall -HUP gunicorn`

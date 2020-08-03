#!/usr/bin/python3.5
# -*- coding: UTF-8 -*-


import os,json,sys,datetime,eventlet,logging

from flask import Flask, render_template, request, jsonify, redirect, make_response, send_file
from flask_mqtt import Mqtt  # mqtt插件

from multiprocessing import Process

from werkzeug.utils import secure_filename  #上传文件插件
from flask_socketio import SocketIO         #接口插件

from flask_apscheduler import APScheduler   #定时插件

hostpath =os.getcwd()
def json_rate(file):
    CONF_PATH=hostpath+'/cmdapi/'+file
    CONF = json.load(open(CONF_PATH))
    return CONF


eventlet.monkey_patch()


if getattr(sys, 'frozen', False):
    template_folder = './templates'
    static_folder = './static'
    app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
else:
    app = Flask(__name__)

mqtt_conf=json_rate("usermqtt.json")
conf=json_rate("conf.json")

app.config['SECRET'] = 'my secret key'
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['MQTT_BROKER_URL'] = mqtt_conf['mqtt']['url']
app.config['MQTT_BROKER_PORT'] = int(mqtt_conf['mqtt']['mtport'])
app.config['MQTT_CLIENT_ID'] = mqtt_conf['mqtt']['id']
app.config['MQTT_CLEAN_SESSION'] = mqtt_conf['mqtt']['cleansession']
app.config['MQTT_USERNAME'] = mqtt_conf['mqtt']['user']
app.config['MQTT_PASSWORD'] = mqtt_conf['mqtt']['pass']
app.config['MQTT_KEEPALIVE'] = int(mqtt_conf['mqtt']['reconnectTimeout'])
app.config['MQTT_TLS_ENABLED'] = mqtt_conf['mqtt']['tls']
app.config['MQTT_LAST_WILL_TOPIC'] = '/loog'
app.config['MQTT_LAST_WILL_MESSAGE'] = 'bye'
app.config['MQTT_LAST_WILL_QOS'] = 0

# Parameters for SSL enabled
# app.config['MQTT_BROKER_PORT'] = 8883
# app.config['MQTT_TLS_ENABLED'] = True
# app.config['MQTT_TLS_INSECURE'] = True
# app.config['MQTT_TLS_CA_CERTS'] = 'ca.crt'

mqtt = Mqtt(app)
socketio = SocketIO(app)
scheduler = APScheduler()


#订阅地址并处理自动消息=========================
mqtt.subscribe('#', 0)

def on_publish(topic,message,qos):
    mqtt.publish(topic, message, qos)

def md5value(s):
    md5 = hashlib.md5()
    md5.update(s)
    return md5.hexdigest()
def hap_homekit():
    os.system('./home.py') 
#json处理=======================================
def json_edit(path,job,val,val0,nub):
              data = json.load(open(path))
              V=eval("data"+val0)
              if nub == 'y':
                  val=int(val)
              else:
                  val=val
              if nub == 'a':
                  data=json.loads(job)
              else:
                  V[val]=json.loads(job)
              
              fs =open(path,'w')   
              fs.write(json.dumps(data))            
              fs.close()
              return {"info":"y","val":""}

def Djson_edit(path,job,val,val0):
              data = json.load(open(path))
              V=eval("data"+val0)
              V[val]=job
              fs =open(path,'w')   
              fs.write(json.dumps(data))            
              fs.close()
              return {"info":"y","val":""}
def rec_sensor(path,job,val,val0):
              data = json.load(open(path))
              data['list'][int(val0)][str(val)]=job
              fs =open(path,'w')   
              fs.write(json.dumps(data))            
              fs.close()
              return {"info":"y","val":val}

def json_add(path,job,val,val0):
              data = json.load(open(path))
              V=eval("data"+val0)
              V[val].append(json.loads(job))
              fs =open(path,'w')   
              fs.write(json.dumps(data))            
              fs.close()
              return {"info":"y","val":""}

def json_down(path):
              response = make_response(send_file(path))
              response.headers["Content-Disposition"] = "attachment; filename=mqtt.json"
              return response

def json_del(path,job,val,val0):
              data = json.load(open(path))
              V=eval("data"+val0)
              V[val].pop(int(job))
              fs =open(path,'w')   
              fs.write(json.dumps(data))            
              fs.close()
              return {"info":"y","val":""}


#自动化系统=====================================
def auto_sys(topic,message):
    if topic=='loog/menkou/POWER':
        if message=='ON': 
            mqtt.publish('loog/keting/cmnd/POWER', 'ON', 0)
    if topic=='loog/menkou/POWER':
        if message=='OFF': 
            mqtt.publish('loog/keting/cmnd/POWER', 'OFF', 0)


def rec_mqtt(topic,message):
    path=hostpath+'/cmdapi/'+'usermqtt.json'
    size=len(mqtt_conf["list"])         
    for i in range(0,size,1):
       if topic==mqtt_conf["list"][int(i)]["Subscribe"]:
         if mqtt_conf["list"][int(i)]["mode"]=='sensor':
           val=json.loads(message)
           rec_sensor(path,val[mqtt_conf["list"][int(i)]["key1"]][mqtt_conf["list"][int(i)]["name"]],"stat",i)
         else:
           rec_sensor(path,message,"stat",i)
@app.route('/')
def index():
    return render_template('index.html')


#系统处理======================================
@app.route('/json')
def rjson():
    email = request.cookies.get('email') 
    conf_name =hostpath+'/cmdapi/usermqtt.json'        
    if not os.path.exists(conf_name.encode("utf8")):
              rjson =json.load(open(hostpath+'/cmdapi/mqtt.json','r'))
              fs =open(conf_name,'w')   
              fs.write(json.dumps(rjson ))
              os.chmod(conf_name, stat.S_IRWXU|stat.S_IRGRP|stat.S_IROTH)
              
    else:           
              rjson = json.load(open(conf_name,'r'))
    return jsonify(rjson)
@app.route('/API')
def edit():
    passwd = request.cookies.get('passwd')
    email = request.cookies.get('email')
    path = hostpath+'/cmdapi/usermqtt.json'
    job = request.args.get('job',type=str,default=None)
    val = request.args.get('val',type=str,default=None)
    val0 = request.args.get('val0',type=str,default=None)
    mode = request.args.get('mode',type=str,default=None)
    nub = request.args.get('nub',type=str,default=None)
    bak_val=''
    if passwd == passwd:
          if mode == 'edit':
             bak_val=json_edit(path,job,val,val0,nub)
          if mode == 'Dedit':
             bak_val=Djson_edit(path,job,val,val0)
          if mode == 'sensor':
             bak_val=rec_sensor(path,job,val,val0)
          if mode == 'add':
             bak_val=json_add(path,job,val,val0)
          if mode == 'del':
             bak_val=json_del(path,job,val,val0)
          if mode == 'down':
             bak_val=json_down(hostpath+'/cmdapi/usermqtt.json')
    return bak_val

@app.route('/upload', methods=['POST'])
def upload():
  passwd = request.cookies.get('passwd')
  email = request.cookies.get('email')
  path = hostpath+'/cmdapi/upfile/'
  if email == email: 
    if request.method == 'POST':
        f = request.files['file']
        filename = secure_filename(f.filename)
        if not os.path.exists(path.encode("utf8")):
                       os.system("mkdir "+path),  
        types = ['json']
        if filename.split('.')[-1] in types:       
                upload_path = os.path.join(path,secure_filename(email+'.json'))
                f.save(upload_path)
                os.chmod(path + email.replace('@',''), stat.S_IRWXU|stat.S_IRGRP|stat.S_IROTH)
                info = {'code':'y','val':'上传完成'}
        else:
                info = {'code':'n','val':'文件格式不支持上传'}

    else:
        info = {'code':'n','val':'模式错误'}
  else:
        info = {'code':'n','val':'请先登录账号'}
  return info
#swmqtt=================
@socketio.on('publish')
def handle_publish(json_str):
    data = json.loads(json_str)
    mqtt.publish(data['topic'], data['message'], data['qos'])


@socketio.on('subscribe')
def handle_subscribe(json_str):
    data = json.loads(json_str)
    mqtt.subscribe(data['topic'], data['qos'])
    #mqtt.subscribe('#', 0)

@socketio.on('unsubscribe_all')
def handle_unsubscribe_all():
    mqtt.unsubscribe_all()

@mqtt.on_message()
def handle_mqtt_message(client, userdata, message):
    data = dict(
        topic=message.topic,
        payload=message.payload.decode(),
        qos=message.qos,
    )
    socketio.emit('mqtt_message', data=data)
    #auto_sys(message.topic,message.payload.decode())
    rec_mqtt(message.topic,message.payload.decode())


@mqtt.on_log()
def handle_logging(client, userdata, level, buf):
    #print(level, buf)
    pass
#系统配置=================
@app.route('/CONF')
def data():
    CONF = json_rate('conf.json')
    return CONF
#天猫认证=================

@app.route('/auth/authorize', methods=['GET','POST'])
def authk(): 
    redirect_uri = request.args.get('redirect_uri',type=str,default=None)
    state = request.args.get('state',type=str,default=None)
    code='21fccc02e29243eabb1cf297268814f1'
    return '<a href="'+str(redirect_uri)+'&code='+str(code)+'&state='+str(state)+'">go</a>'
@app.route('/token', methods=['GET','POST'])
def token(): 
    data=json_rate('conf.json')
    return data['tmall']['token']
@app.route('/auth/token', methods=['GET','POST'])
def auth_token(): 
    data=json_rate('conf.json')
    return data['tmall']['token']


@app.route('/aligenie', methods=['GET','POST'])
def aligenie():
    data=json.loads(request.get_data(as_text=True))
    conf=json_rate('usermqtt.json')
    size=len(conf["list"])
    for i in range(0,size,1):
        deviceId=conf["list"][int(i)]["mode"]+'.'+conf["list"][int(i)]["name"]
        if data['payload']['deviceId']==str(deviceId):
                on_publish(conf["list"][int(i)]["Publish"],data['payload']['value'],0)
        if data['header']['name']=="TurnOn":
                callval="TurnOnResponse"
        if data['header']['name']=="TurnOff":
                callval="TurnOffResponse"
    callbak={
  "header":{
      "namespace":"AliGenie.Iot.Device.Control",
      "name":callval,
      "messageId":data['header']['messageId'],
      "payLoadVersion":1
   },
   "payload":{
      "deviceId":data['payload']['deviceId']
    }
 }
    return callbak
#定时任务=================
@app.route('/pause', methods=['GET','POST'])
def pausetask():  # 暂停
    data = request.args.get('id',type=str,default=None)
    scheduler.pause_job(str(data))
    return {'info':'y','val':'ok'}


@app.route('/resume', methods=['GET','POST'])
def resumetask():  # 恢复
    data = request.args.get('id',type=str,default=None)
    scheduler.resume_job(str(data))
    return {'info':'y','val':'ok'}

@app.route('/gettask', methods=['GET','POST'])
def get_task():  # 获取
    list=[];
    for job in scheduler.get_jobs(): 
        list.append(job.id)
    return json.dumps(list)


@app.route('/remove_task', methods=['GET','POST'])
def remove_task():  # 移除
    data = request.args.get('id',type=str,default=None)
    scheduler.remove_job('ID'+str(data))
    return {'info':'y','val':'ok'}


@app.route('/addjob', methods=['GET', 'POST'])
def addtask():
    id = request.args.get('id',type=str,default=None)
    cmd = request.args.get('cmd',type=str,default=None)
    mode = request.args.get('mode',type=str,default=None)
    publish = request.args.get('time_list_Publish',type=str,default=None)
    email = request.cookies.get('email') 
    week= request.args.get('week',type=str,default=None)
    hour= request.args.get('hour',type=str,default=None)
    minute= request.args.get('minute',type=str,default=None)
    second= request.args.get('second',type=str,default=None)
    if mode == 'cron':
        scheduler.add_job(func=on_publish, id='ID'+str(id), args=(publish, cmd, 0), trigger='cron', day_of_week=week, hour=hour, minute=minute,
                          second=10,
                          replace_existing=True)
        # trigger='cron' 表示是一个定时任务
    if mode == 'interval':
        scheduler.add_job(func=on_publish, id='ID'+str(id), args=(publish, cmd, 0), trigger='interval', seconds=int(second),
                          replace_existing=True)
        # trigger='interval' 表示是一个循环任务，每隔多久执行一次
    return {'info':'y','val':'ok'}


if __name__ == '__main__':
    scheduler.init_app(app=app)
    scheduler.start()
    if str(conf['hap_homkit']) == 'y':
          p = Process(target=hap_homekit, args=())
          p.start() 
          
    socketio.run(app, host='0.0.0.0', port=int(conf['port']),use_reloader=False, debug=True)



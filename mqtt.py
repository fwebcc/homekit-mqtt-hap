#!/usr/bin/python3.5
# -*- coding: UTF-8 -*-

"""Starts a fake fan, lightbulb, garage door and a TemperatureSensor
"""
import logging
import signal
import random,os,json,datetime,math
from pyhap.iid_manager import IIDManager
import paho.mqtt.client as mqtt            # MQTT插件

import subprocess
from pyhap.accessory import Accessory, Bridge
from pyhap.accessory_driver import AccessoryDriver
from pyhap.const import (CATEGORY_FAN,
                         CATEGORY_LIGHTBULB,
                         CATEGORY_GARAGE_DOOR_OPENER,
                         CATEGORY_DOOR_LOCK,
                         CATEGORY_SWITCH,
                         CATEGORY_SENSOR)


logging.basicConfig(level=logging.INFO, format="[%(module)s] %(message)s")

hostpath =os.getcwd()
def json_rate(file):
    CONF_PATH=hostpath+'/cmdapi/'+file
    CONFS = json.load(open(CONF_PATH))
    return CONFS

mqtt_conf=json_rate("usermqtt.json")
conf=json_rate("conf.json")

mqtt = mqtt.Client("python")
# 连接MQTT服务器
def on_mqtt_connect():
        CONF=json_rate("usermqtt.json")
        MQTTHOST = mqtt_conf['mqtt']['url']
        MQTTPORT = mqtt_conf['mqtt']['mtport']

        # 用户名
        username = mqtt_conf['mqtt']['user']
        # 密码
        password = mqtt_conf['mqtt']['pass']
        # 订阅主题名
        topic = '#'

        mqtt.username_pw_set(username, password)
        mqtt.connect(MQTTHOST, int(MQTTPORT), 60)
        mqtt.loop_start()
        #mqtt.loop_forever()


# publish 发送消息
def on_publish(topic, payload, qos):   
    mqtt.publish(topic, payload, qos)

# 消息处理函数
def on_message(mqtt,obj, msg):
    curtime = datetime.datetime.now()
    strcurtime = curtime.strftime("%Y-%m-%d %H:%M:%S")
    print(strcurtime + ": " +str(msg.topic) + ":" + str(msg.payload))

def on_exec(strcmd):
    print (strcmd)


# subscribe 接受消息
def on_subscribe():
    mqtt.subscribe('#', 1)
    mqtt.on_message = on_message


new_mode=[]


#homekit=============================


class DisplaySwitch(Accessory):
    """
    An accessory that will display, and allow setting, the display status
    of the Mac that this code is running on.
    """

    category = CATEGORY_SWITCH

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        serv_switch = self.add_preload_service('Switch')
        self.display = serv_switch.configure_char(
                      'On', setter_callback=self.set_display)
        size=len(mqtt_conf["list"])         
        for i in range(0,size,1):    
                           
              if str(mqtt_conf["list"][int(i)]["title"]) == str(self.display_name) : 
                 if str(mqtt_conf["list"][int(i)]["stat"]).upper()== str(mqtt_conf["list"][int(i)]["cmdon"]).upper() :
                          self.display.set_value(1)
                 else:
                          self.display.set_value(0)

    def set_display(self, value):
        logging.info("switch: %s", value)       
        if value==1:
            payload='ON'
        else:            
            payload='OFF' 
        homekit_mqtt_Publish(self.display_name,payload)    
 
    def run(self): 
        aid={'title':self.display_name,'aid':str(self.aid)}
        new_mode.append(aid)



class TemperatureSensor(Accessory):

    category = CATEGORY_SENSOR

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        serv_temp = self.add_preload_service('TemperatureSensor')
        self.char_temp = serv_temp.get_characteristic('CurrentTemperature')


    @Accessory.run_at_interval(3)
    def run(self):
        size=len(mqtt_conf["list"])         
        for i in range(0,size,1):               
              if str(mqtt_conf["list"][int(i)]["title"]) == str(self.display_name): 
                   self.char_temp.set_value(int(mqtt_conf["list"][int(i)]["stat"]))



class FakeFan(Accessory):
    """Fake Fan, only logs whatever the client set."""

    category = CATEGORY_FAN

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Add the fan service. Also add optional characteristics to it.
        serv_fan = self.add_preload_service(
            'Fan', chars=['RotationSpeed', 'RotationDirection'])

        self.char_rotation_speed = serv_fan.configure_char(
            'RotationSpeed', setter_callback=self.set_rotation_speed)
        self.char_rotation_direction = serv_fan.configure_char(
            'RotationDirection', setter_callback=self.set_rotation_direction)

    def set_rotation_speed(self, value):
        logging.debug("Rotation speed changed: %s", value)

    def set_rotation_direction(self, value):
        logging.debug("Rotation direction changed: %s", value)

class LightBulb(Accessory):
    """Fake lightbulb, logs what the client sets."""

    category = CATEGORY_LIGHTBULB

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        serv_light = self.add_preload_service('Lightbulb')
        self.char_on = serv_light.configure_char(
            'On', setter_callback=self.set_bulb)


    def set_bulb(self, value):
        logging.info("Bulb value: %s", value)       
        if value==1:
            payload='ON'
        else:            
            payload='OFF' 
        homekit_mqtt_Publish(self.display_name,payload)     

    def run(self): 
        aid={'title':self.display_name,'aid':str(self.aid)}
        new_mode.append(aid)
        #print(self)  

class GarageDoor(Accessory):
    """Fake garage door."""

    category = CATEGORY_GARAGE_DOOR_OPENER

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        char_door=self.add_preload_service('GarageDoorOpener')
        self.char_stat=char_door.configure_char('TargetDoorState',setter_callback=self.change_state)
        


    def change_state(self, value):
        logging.info("Bulb value: %s", value)
        self.get_service('GarageDoorOpener')\
            .get_characteristic('CurrentDoorState')\
            .set_value(value)


        if value==1:
            payload='OFF'
            value2=1
        else:            
            payload='ON' 
            value2=0
        homekit_mqtt_Publish(self.display_name,payload)



    def run(self): 
        aid={'title':self.display_name,'aid':str(self.aid)}
        new_mode.append(aid)

class cmqtt(Accessory):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        mqtt.subscribe('#', 1)
        mqtt.on_message = self.on_mqtt


    def on_mqtt(self,mqtt,obj, msg):

        old_name=self.display_name
        old_id=self.aid


        size=len(mqtt_conf["list"])         
        for i in range(0,size,1):    
                           
              if str(mqtt_conf["list"][int(i)]["Subscribe"]) == str(msg.topic) : 
                      title=mqtt_conf["list"][int(i)]["title"]

                      mode=mqtt_conf["list"][int(i)]["mode"]
                      self.display_name = title
                      cmdon=mqtt_conf["list"][int(i)]["cmdon"]

                      aid=''
                      for x in new_mode:
                         if x['title']==title:
                                 aid=x['aid']
                      self.aid=int(aid)

                      if mode=='light':                 

                            self.rest_server()

                            serv_light = self.add_preload_service('Lightbulb')
                            self.char_stat = serv_light.configure_char('On') 


                            if str(msg.payload.upper(), "utf-8")==str(cmdon).upper():
                                self.char_stat.set_value(1)
                            else:
                                self.char_stat.set_value(0)

                      if mode=='lock':

                            self.rest_server()

                            char_door=self.add_preload_service('GarageDoorOpener')
                            self.char_lock=char_door.configure_char('TargetDoorState') 
                            #self.char_stat1=self.get_service('GarageDoorOpener')
                            #self.char_stat=self.char_stat1.get_characteristic('CurrentDoorState')
                            print('门锁0000000000')
                            if str(msg.payload.upper(), "utf-8")==str(cmdon).upper():
                                self.char_lock.set_value(0)
                                print('开门9999999')
                                self.get_service('GarageDoorOpener')\
                                    .get_characteristic('CurrentDoorState')\
                                    .set_value(0)
                            else:
                                self.char_lock.set_value(1)
                                print('关门9999999')
                                self.get_service('GarageDoorOpener')\
                                    .get_characteristic('CurrentDoorState')\
                                    .set_value(1)
                      if mode=='switch':

                            self.rest_server()

                            serv_switch = self.add_preload_service('Switch')
                            self.display = serv_switch.configure_char('On') 
                            if str(msg.payload.upper(), "utf-8")==str(cmdon).upper():
                                self.display.set_value(1)
                            else:
                                self.display.set_value(0)

                      #print(title,aid,cmdon,msg.topic,str(mqtt_conf["list"][int(i)]["Subscribe"]))

        print(title,self,'==============') 
        self.display_name=old_name
        self.aid=old_id
    def rest_server(self):       
                            self.driver = driver
                            self.services = []
                            self.iid_manager = IIDManager()

                            self.add_info_service()
                            self._set_services()




def get_bridge(driver):
    bridge = Bridge(driver, 'Bridge')
    size=len(mqtt_conf["list"])
    for i in range(0,size,1):
        if str(mqtt_conf["list"][int(i)]["mode"])=='light':
             bridge.add_accessory(LightBulb(driver,mqtt_conf["list"][int(i)]["title"]))
        if str(mqtt_conf["list"][int(i)]["mode"])=='sensor':
             bridge.add_accessory(TemperatureSensor(driver,mqtt_conf["list"][int(i)]["title"]))
        if str(mqtt_conf["list"][int(i)]["mode"])=='lock':
             bridge.add_accessory(GarageDoor(driver,mqtt_conf["list"][int(i)]["title"])) 
        if str(mqtt_conf["list"][int(i)]["mode"])=='switch':
             bridge.add_accessory(DisplaySwitch(driver,mqtt_conf["list"][int(i)]["title"]))
          
    #bridge.add_accessory(FakeFan(driver, 'Big Fan'))

    return bridge

def homekit_mqtt_Publish(title,payload):
        size=len(mqtt_conf["list"])
        Publish=''
        for i in range(0,size,1):
           if str(mqtt_conf["list"][int(i)]["title"])==title:
              Publish=mqtt_conf["list"][int(i)]["Publish"]
        on_publish(Publish, payload, 0)



on_mqtt_connect()
driver = AccessoryDriver(port=51826, persist_file='busy_home.state')
driver.add_accessory(accessory=get_bridge(driver))
cmqtt(driver,'') 
signal.signal(signal.SIGTERM, driver.signal_handler)

driver.start()
#homkit==========

import logging
import signal
import json
import os
from pyhap.accessory import Accessory, Bridge
from pyhap.accessory_driver import AccessoryDriver
from pyhap.const import (CATEGORY_FAN, CATEGORY_LIGHTBULB,
                         CATEGORY_GARAGE_DOOR_OPENER, CATEGORY_SENSOR, CATEGORY_SWITCH)
import paho.mqtt.client as mqtt

# 配置日志
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

def load_json(file_name):
    try:
        with open(os.path.join(os.getcwd(), file_name), 'r') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Failed to load {file_name}: {e}")
        return {}

# 1. --- 基础配件类优化 ---

class BaseMqttAccessory(Accessory):
    """基类：处理通用的 MQTT 发送逻辑"""
    def __init__(self, driver, config, *args, **kwargs):
        super().__init__(driver, config['title'], *args, **kwargs)
        self.config = config
        self.publish_topic = config.get('Publish', '')
        self.cmdon = str(config.get('cmdon', 'ON')).upper()
        self.cmdoff = str(config.get('cmdoff', 'OFF')).upper()

    def mqtt_publish(self, payload):
        if self.publish_topic:
            self.driver.mqtt_client.publish(self.publish_topic, payload, qos=0)

class MqttSwitch(BaseMqttAccessory):
    category = CATEGORY_SWITCH
    def __init__(self, driver, config):
        super().__init__(driver, config)
        serv = self.add_preload_service('Switch')
        self.char_on = serv.configure_char('On', setter_callback=self.set_switch)
    
    def set_switch(self, value):
        payload = self.cmdon if value else self.cmdoff
        self.mqtt_publish(payload)

    def update_state(self, payload):
        """由外部调用更新状态"""
        self.char_on.set_value(1 if payload == self.cmdon else 0)

class MqttLight(BaseMqttAccessory):
    category = CATEGORY_LIGHTBULB
    def __init__(self, driver, config):
        super().__init__(driver, config)
        serv = self.add_preload_service('Lightbulb')
        self.char_on = serv.configure_char('On', setter_callback=self.set_light)

    def set_light(self, value):
        self.mqtt_publish(self.cmdon if value else self.cmdoff)

    def update_state(self, payload):
        self.char_on.set_value(1 if payload == self.cmdon else 0)

class MqttTemperature(BaseMqttAccessory):
    category = CATEGORY_SENSOR
    def __init__(self, driver, config):
        super().__init__(driver, config)
        serv = self.add_preload_service('TemperatureSensor')
        self.char_temp = serv.get_characteristic('CurrentTemperature')

    def update_state(self, payload):
        try:
            self.char_temp.set_value(float(payload))
        except ValueError:
            pass

# 2. --- MQTT 中控逻辑 ---

class MqttManager:
    """管理所有配件的订阅和分发"""
    def __init__(self, config, accessories):
        self.config = config['mqtt']
        self.accessories = accessories # {topic: accessory_object}
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def start(self):
        self.client.username_pw_set(self.config['user'], self.config['pass'])
        self.client.connect(self.config['url'], int(self.config['mtport']), 60)
        self.client.loop_start()

    def on_connect(self, client, userdata, flags, rc):
        logging.info(f"MQTT Connected with result code {rc}")
        # 只订阅配置文件中存在的 Topic
        for topic in self.accessories.keys():
            if topic:
                client.subscribe(topic)

    def on_message(self, client, userdata, msg):
        payload = str(msg.payload.decode("utf-8")).upper()
        topic = msg.topic
        if topic in self.accessories:
            acc = self.accessories[topic]
            logging.info(f"Updating {acc.display_name} via {topic}: {payload}")
            # 调用配件自己的更新方法，触发 HomeKit 状态推送
            acc.update_state(payload)

# 3. --- 主程序运行 ---

def main():
    mqtt_conf = load_json("confing.json")
    if not mqtt_conf: return

    driver = AccessoryDriver(port=51826, persist_file='busy_home.state')
    bridge = Bridge(driver, 'SmartBridge')
    
    # 建立映射表: {SubscribeTopic: AccessoryObject}
    topic_map = {}
    
    # 初始化配件
    for item in mqtt_conf.get("list", []):
        mode = item.get("mode")
        acc = None
        
        if mode == 'light':
            acc = MqttLight(driver, item)
        elif mode == 'switch':
            acc = MqttSwitch(driver, item)
        elif mode == 'sensor':
            acc = MqttTemperature(driver, item)
        # 可继续扩展其他模式...

        if acc:
            bridge.add_accessory(acc)
            topic_map[item.get("Subscribe")] = acc

    driver.add_accessory(accessory=bridge)

    # 启动 MQTT 管理器
    mqtt_manager = MqttManager(mqtt_conf, topic_map)
    driver.mqtt_client = mqtt_manager.client # 注入给配件使用
    mqtt_manager.start()

    # 信号处理
    signal.signal(signal.SIGTERM, driver.signal_handler)
    driver.start()

if __name__ == "__main__":
    main()

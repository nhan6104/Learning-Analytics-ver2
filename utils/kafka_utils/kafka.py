from kafka import KafkaProducer, KafkaConsumer


class KafkaUtils:
    def __init__(self):
        pass
        # self.bootstrap_servers = bootstrap_servers

    def create_producer(self, bootstrapServers):
        """Create and return a Kafka producer."""
        producer = KafkaProducer(bootstrap_servers=bootstrapServers)
        return producer

    def create_consumer(self, bootstrapServers, topic, group_id=None, auto_offset_reset='earliest'):
        """Create and return a Kafka consumer."""
        consumer = KafkaConsumer(
            topic,
            bootstrap_servers=bootstrapServers,
            group_id=group_id,
            auto_offset_reset=auto_offset_reset
        )
        return consumer
    

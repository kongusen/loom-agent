
import type { CloudEvent } from '../types';

type EventHandler = (event: CloudEvent) => void;

class WebSocketService {
  private ws: WebSocket | null = null;
  private listeners: EventHandler[] = [];
  private url: string = "ws://localhost:8765/ws/events";
  private reconnectInterval: number = 2000;

  connect() {
    this.ws = new WebSocket(this.url);

    this.ws.onopen = () => {
      console.log('Connected to Loom Studio Server');
    };

    this.ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        if (message.type === 'event' && message.data) {
          this.notify(message.data);
        } else if (message.type === 'topology' && message.data) {
          this.notifyTopology(message.data);
        }
      } catch (err) {
        console.error('Failed to parse message', err);
      }
    };

    this.ws.onclose = () => {
      console.log('Disconnected from Loom Studio Server');
      setTimeout(() => this.connect(), this.reconnectInterval);
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      this.ws?.close();
    };
  }

  subscribe(handler: EventHandler) {
    this.listeners.push(handler);
    return () => {
      this.listeners = this.listeners.filter(h => h !== handler);
    };
  }

  private notify(event: CloudEvent) {
    this.listeners.forEach(h => h(event));
  }

  // 添加拓扑更新监听器
  private topologyListeners: Array<(topology: any) => void> = [];

  subscribeTopology(handler: (topology: any) => void) {
    this.topologyListeners.push(handler);
    return () => {
      this.topologyListeners = this.topologyListeners.filter(h => h !== handler);
    };
  }

  private notifyTopology(topology: any) {
    this.topologyListeners.forEach(h => h(topology));
  }
}

export const wsService = new WebSocketService();

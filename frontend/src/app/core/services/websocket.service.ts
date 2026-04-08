import { Injectable, OnDestroy, signal } from '@angular/core';
import { environment } from '../../../environments/environment';

export interface WsMessage {
  type: string;
  tick?: number;
  data?: unknown;
}

@Injectable({ providedIn: 'root' })
export class WebSocketService implements OnDestroy {
  private socket: WebSocket | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private currentSimId: string | null = null;

  connected = signal(false);
  lastMessage = signal<WsMessage | null>(null);

  connect(simulationId: string): void {
    this.currentSimId = simulationId;
    this.disconnect();
    const url = `${environment.wsUrl}/ws/simulations/${simulationId}`;
    this.socket = new WebSocket(url);

    this.socket.onopen = () => {
      this.connected.set(true);
    };

    this.socket.onmessage = (event) => {
      try {
        const msg: WsMessage = JSON.parse(event.data);
        this.lastMessage.set(msg);
      } catch {
        // ignore malformed messages
      }
    };

    this.socket.onclose = () => {
      this.connected.set(false);
      this.scheduleReconnect();
    };

    this.socket.onerror = () => {
      this.connected.set(false);
    };
  }

  disconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
    this.connected.set(false);
  }

  send(message: unknown): void {
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(message));
    }
  }

  private scheduleReconnect(): void {
    if (this.currentSimId) {
      this.reconnectTimer = setTimeout(() => {
        if (this.currentSimId) {
          this.connect(this.currentSimId);
        }
      }, 3000);
    }
  }

  ngOnDestroy(): void {
    this.disconnect();
  }
}

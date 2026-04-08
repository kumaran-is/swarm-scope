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
  private reconnectDelay = 3000;
  private reconnectAttempts = 0;

  connected = signal(false);
  lastMessage = signal<WsMessage | null>(null);

  connect(simulationId: string): void {
    this.currentSimId = simulationId;
    this.disconnect();
    const url = `${environment.wsUrl}/ws/simulations/${simulationId}`;
    this.socket = new WebSocket(url);

    this.socket.onopen = () => {
      this.connected.set(true);
      this.reconnectAttempts = 0;
      this.reconnectDelay = 3000;
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
      this.reconnectAttempts++;
      // Exponential backoff: 3s, 6s, 12s, max 30s
      this.reconnectDelay = Math.min(3000 * Math.pow(2, this.reconnectAttempts - 1), 30000);
      this.reconnectTimer = setTimeout(() => {
        if (this.currentSimId) {
          this.connect(this.currentSimId);
        }
      }, this.reconnectDelay);
    }
  }

  ngOnDestroy(): void {
    this.disconnect();
  }
}

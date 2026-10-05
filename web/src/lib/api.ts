import { env } from '$env/dynamic/public';
import type { BackendHealth, ForecastRequest, ForecastResponse } from './types';

function getConfiguredApiUrl(): string | undefined {
	return (env.PUBLIC_API_URL || (import.meta.env?.PUBLIC_API_URL as string | undefined))?.trim().replace(/\/+$/, '') || undefined;
}

function getTargetEndpoints(path: string): string[] {
	const configured = getConfiguredApiUrl();
	const list: string[] = [];

	if (configured) {
		list.push(`${configured}${path}`);
	}
	// Vite dev proxy
	list.push(`/api${path}`);
	// Local direct backend (for local dev environments)
	if (typeof window !== 'undefined' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')) {
		list.push(`http://127.0.0.1:8000${path}`);
	}

	return Array.from(new Set(list));
}

export async function checkBackendHealth(): Promise<BackendHealth> {
	const hasConfiguredRemote = Boolean(getConfiguredApiUrl());
	const timeoutMs = hasConfiguredRemote ? 6000 : 2500;
	const endpoints = getTargetEndpoints('/health');

	for (const endpoint of endpoints) {
		try {
			const res = await fetch(endpoint, {
				method: 'GET',
				signal: AbortSignal.timeout(timeoutMs)
			});
			if (res.ok) {
				const data = await res.json();
				return {
					status: 'healthy',
					service: data.service,
					manifest: data.manifest
				};
			}
		} catch {
			// Try next candidate endpoint
		}
	}

	return { status: 'offline', error: 'Backend unreachable or starting up' };
}

export class BackendRejectionError extends Error {
	status: number;
	constructor(message: string, status: number) {
		super(message);
		this.name = 'BackendRejectionError';
		this.status = status;
	}
}

export async function requestForecast(payload: ForecastRequest): Promise<{
	data: ForecastResponse;
	isLiveBackend: boolean;
	source: string;
}> {
	const hasConfiguredRemote = Boolean(getConfiguredApiUrl());
	// Extended timeout (25s) allows Render free-tier cold boot to finish on initial request
	const timeoutMs = hasConfiguredRemote ? 25000 : 4000;
	const targets = getTargetEndpoints('/forecast/24h');

	for (const endpoint of targets) {
		try {
			const res = await fetch(endpoint, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(payload),
				signal: AbortSignal.timeout(timeoutMs)
			});

			if (res.ok) {
				const json = await res.json();
				return {
					data: json,
					isLiveBackend: true,
					source: endpoint
				};
			} else if (res.status >= 400 && res.status < 600) {
				// The backend is actively reachable and deliberately rejected the input or encountered an error
				const errData = await res.json().catch(() => ({}));
				const detailMsg = typeof errData.detail === 'string'
					? errData.detail
					: (Array.isArray(errData.detail)
						? errData.detail.map((d: any) => d.msg || JSON.stringify(d)).join('; ')
						: (errData.detail ? JSON.stringify(errData.detail) : `Forecast rejected by backend (${res.status})`));
				throw new BackendRejectionError(detailMsg, res.status);
			}
		} catch (e: any) {
			// If it's a backend rejection (validation, telemetry gap, or server error), rethrow to notify operator
			if (e instanceof BackendRejectionError) {
				throw e;
			}
			// Otherwise network connection failed; proceed to next target or simulation fallback
		}
	}

	// Simulation fallback when backend is offline
	const t0 = performance.now();
	const timestamps: string[] = [];
	const p_pv_forecast: number[] = [];
	const p_load_forecast: number[] = [];

	for (let h = 0; h < 24; h++) {
		const step = payload.weather_forecast[h];
		if (!step) continue;
		timestamps.push(step.timestamp);

		const ghi = step.ghi;
		const temp = step.temp_amb;

		// Physical rules
		let pv = 0.0;
		if (ghi > 0) {
			const derate = Math.max(0.7, Math.min(1.1, 1 - 0.004 * (temp - 25)));
			pv = Math.min(50.0, 50.0 * (ghi / 1000) * derate);
		}

		// Parse as UTC ISO to preserve site wall-clock hour across all client timezones
		const stepDate = new Date(step.timestamp.endsWith('Z') ? step.timestamp : step.timestamp + 'Z');
		const hour = stepDate.getUTCHours();
		const isWeekend = stepDate.getUTCDay() === 0 || stepDate.getUTCDay() === 6;
		const diurnal = [
			0.28, 0.25, 0.24, 0.24, 0.26, 0.32,
			0.50, 0.75, 0.85, 0.78, 0.72, 0.70,
			0.68, 0.67, 0.69, 0.72, 0.76, 0.82,
			0.95, 1.00, 0.92, 0.78, 0.55, 0.38
		][hour % 24];

		const hvac = Math.max(0, temp - 22) * 0.45 + Math.max(0, 16 - temp) * 0.35;
		let load = 10.0 + (27.0 * diurnal * (isWeekend ? 0.82 : 1.0)) + hvac;
		load = Math.max(10.0, Math.min(45.0, load));

		p_pv_forecast.push(Math.round(pv * 100) / 100);
		p_load_forecast.push(Math.round(load * 100) / 100);
	}

	const latency = Math.round((performance.now() - t0) * 100) / 100;

	return {
		data: {
			timestamps,
			p_pv_forecast,
			p_load_forecast,
			metadata: {
				origin: payload.origin,
				execution_time_ms: latency
			}
		},
		isLiveBackend: false,
		source: 'Client-Side Physical Simulation Engine'
	};
}

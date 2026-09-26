import { afterEach, describe, expect, it, vi } from 'vitest';
import { BackendRejectionError, requestForecast } from './api';
import { generateScenarioData } from './telemetry';

describe('API Client & Forecasting Pipeline Fallback', () => {
	afterEach(() => {
		vi.restoreAllMocks();
	});

	it('generates a valid 24-step forecast payload via simulation engine fallback', async () => {
		vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('Backend offline'));

		const origin = '2026-06-15T12:00:00';
		const { history, weather } = generateScenarioData(origin);

		const result = await requestForecast({
			origin,
			history,
			weather_forecast: weather
		});

		expect(result.data).toBeDefined();
		expect(result.data.timestamps.length).toBe(24);
		expect(result.data.p_pv_forecast.length).toBe(24);
		expect(result.data.p_load_forecast.length).toBe(24);

		// Assert physical bounds
		for (const val of result.data.p_pv_forecast) {
			expect(val).toBeGreaterThanOrEqual(0);
			expect(val).toBeLessThanOrEqual(50.0);
		}

		for (const val of result.data.p_load_forecast) {
			expect(val).toBeGreaterThanOrEqual(0);
			expect(val).toBeLessThanOrEqual(54.0);
		}

		expect(result.data.metadata.execution_time_ms).toBeGreaterThanOrEqual(0);
		expect(result.isLiveBackend).toBe(false);
	});

	it('rethrows BackendRejectionError on HTTP 422 telemetry gap without falling back to simulation', async () => {
		vi.spyOn(globalThis, 'fetch').mockImplementation(async () => {
			return new Response(
				JSON.stringify({
					detail: 'Telemetry gap exceeds maximum threshold: Consecutive sensor dropout of 4h'
				}),
				{
					status: 422,
					headers: { 'Content-Type': 'application/json' }
				}
			);
		});

		const origin = '2026-06-15T12:00:00';
		const { history, weather } = generateScenarioData(origin, 4);

		await expect(
			requestForecast({
				origin,
				history,
				weather_forecast: weather
			})
		).rejects.toThrowError(BackendRejectionError);
	});

	it('returns live backend payload when fetch succeeds with 200 OK', async () => {
		const mockResponse = {
			timestamps: Array.from({ length: 24 }, (_, i) => `2026-06-15T${String(i + 1).padStart(2, '0')}:00:00`),
			p_pv_forecast: Array.from({ length: 24 }, () => 15.5),
			p_load_forecast: Array.from({ length: 24 }, () => 22.0),
			metadata: {
				origin: '2026-06-15T12:00:00',
				execution_time_ms: 12.4
			}
		};

		vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
			new Response(JSON.stringify(mockResponse), {
				status: 200,
				headers: { 'Content-Type': 'application/json' }
			})
		);

		const origin = '2026-06-15T12:00:00';
		const { history, weather } = generateScenarioData(origin);

		const result = await requestForecast({
			origin,
			history,
			weather_forecast: weather
		});

		expect(result.isLiveBackend).toBe(true);
		expect(result.data.p_pv_forecast[0]).toBe(15.5);
		expect(result.data.metadata.execution_time_ms).toBe(12.4);
	});
});

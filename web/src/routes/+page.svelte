<script lang="ts">
	import { onMount } from 'svelte';
	import { checkBackendHealth, requestForecast } from '$lib/api';
	import { generateScenarioData, SCENARIO_PRESETS } from '$lib/telemetry';
	import type { BackendHealth, ForecastResponse, HistoricalReading, WeatherForecastStep } from '$lib/types';
	import ForecastChart from '$lib/components/ForecastChart.svelte';
	import PipelineSteps from '$lib/components/PipelineSteps.svelte';
	import TelemetryDrawer from '$lib/components/TelemetryDrawer.svelte';
	import InfoModal from '$lib/components/InfoModal.svelte';

	// State
	let selectedScenarioId = $state('summer-peak');
	let customOrigin = $state('2026-06-15T12:00:00');
	let injectGap = $state(false);
	let gapHours = $state(2);

	let backendHealth = $state<BackendHealth>({ status: 'checking' });
	let isRunning = $state(false);
	let isLiveBackend = $state(false);
	let executionSource = $state('');
	let showInfoModal = $state(false);
	let pipelineError = $state<string | null>(null);

	let historyData = $state<HistoricalReading[]>([]);
	let weatherData = $state<WeatherForecastStep[]>([]);
	let forecastResult = $state<ForecastResponse | null>(null);

	let currentPreset = $derived(
		SCENARIO_PRESETS.find((p) => p.id === selectedScenarioId) || SCENARIO_PRESETS[0]
	);

	let totalPvKwh = $derived(
		forecastResult ? forecastResult.p_pv_forecast.reduce((a, b) => a + b, 0) : 0
	);
	let totalLoadKwh = $derived(
		forecastResult ? forecastResult.p_load_forecast.reduce((a, b) => a + b, 0) : 0
	);
	let peakPvKw = $derived(
		forecastResult && forecastResult.p_pv_forecast.length
			? Math.max(...forecastResult.p_pv_forecast)
			: 0
	);
	let peakLoadKw = $derived(
		forecastResult && forecastResult.p_load_forecast.length
			? Math.max(...forecastResult.p_load_forecast)
			: 0
	);
	let netBalanceKwh = $derived(totalPvKwh - totalLoadKwh);
	let daylightHoursCount = $derived(
		weatherData.filter((w) => w.ghi > 0).length
	);

	function loadScenario(presetId: string) {
		selectedScenarioId = presetId;
		pipelineError = null;
		const preset = SCENARIO_PRESETS.find((p) => p.id === presetId);
		if (preset) {
			customOrigin = preset.origin;
			injectGap = Boolean(preset.hasGap);
			gapHours = preset.gapHours || 2;
			runPipeline();
		}
	}

	async function runPipeline() {
		isRunning = true;
		pipelineError = null;

		try {
			const { history, weather } = generateScenarioData(customOrigin, injectGap ? gapHours : 0);
			historyData = history;
			weatherData = weather;

			const res = await requestForecast({
				origin: customOrigin,
				history: historyData,
				weather_forecast: weatherData
			});

			forecastResult = res.data;
			isLiveBackend = res.isLiveBackend;
			executionSource = res.source;
		} catch (err: any) {
			console.error('Forecast generation error:', err);
			pipelineError = err?.message || 'Failed to generate 24-hour forecast from backend.';
		} finally {
			isRunning = false;
		}
	}

	async function refreshHealth() {
		backendHealth = await checkBackendHealth();
	}

	function adjustOriginHours(deltaHours: number) {
		try {
			// Parse with UTC semantics to step wall-clock time without timezone distortion
			const current = new Date(customOrigin.endsWith('Z') ? customOrigin : customOrigin + 'Z');
			current.setUTCHours(current.getUTCHours() + deltaHours);
			const y = current.getUTCFullYear();
			const m = String(current.getUTCMonth() + 1).padStart(2, '0');
			const d = String(current.getUTCDate()).padStart(2, '0');
			const h = String(current.getUTCHours()).padStart(2, '0');
			customOrigin = `${y}-${m}-${d}T${h}:00`;
			runPipeline();
		} catch (e) {
			console.error('Failed to adjust origin', e);
		}
	}

	function setOriginToNow() {
		const now = new Date();
		const y = now.getFullYear();
		const m = String(now.getMonth() + 1).padStart(2, '0');
		const d = String(now.getDate()).padStart(2, '0');
		const h = String(now.getHours()).padStart(2, '0');
		customOrigin = `${y}-${m}-${d}T${h}:00`;
		runPipeline();
	}

	onMount(async () => {
		await refreshHealth();
		loadScenario('summer-peak');
	});
</script>

<main class="page-viewport">
	<div class="page-container">
		<!-- Minimal, Clean Navigation Bar -->
		<nav class="app-nav">
			<div class="nav-brand">
				<span class="brand-name">Helios</span>
				<span class="brand-divider">/</span>
				<span class="brand-context">Microgrid Forecast & Dispatch</span>
			</div>

			<div class="nav-meta">
				<div class="ratings-spec font-mono">
					<span>50 kW PV</span>
					<span class="spec-divider">•</span>
					<span>45 kW Load</span>
				</div>

				<button
					class="status-indicator font-mono"
					class:online={backendHealth.status === 'healthy'}
					class:offline={backendHealth.status === 'offline'}
					onclick={refreshHealth}
					title="Re-check backend API status"
				>
					<span class="status-dot"></span>
					{#if backendHealth.status === 'healthy'}
						<span>API online</span>
					{:else if backendHealth.status === 'offline'}
						<span>Simulation mode</span>
					{:else}
						<span>Connecting...</span>
					{/if}
				</button>

				<button
					class="doc-link-btn"
					onclick={() => (showInfoModal = true)}
				>
					<span>Architecture guide</span>
					<span class="btn-icon" aria-hidden="true">
						<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"><path d="M4.5 11.5l7-7M5.5 4.5h6v6" /></svg>
					</span>
				</button>
			</div>
		</nav>

		<!-- Hero Section -->
		<header class="hero-header">
			<h1 class="hero-title">
				24-hour solar generation, building load forecasting & <em>battery dispatch</em>
			</h1>
			<p class="hero-description">
				Conditioned machine learning pipeline providing synchronous day-ahead power predictions and physical boundary enforcement for economic storage optimization.
			</p>
		</header>

		<!-- Hero Key Metrics -->
		{#if forecastResult}
			<section class="kpi-grid">
				<div class="kpi-box">
					<div class="kpi-label-row">
						<span class="kpi-pip pv-pip"></span>
						<span class="kpi-label">Solar PV forecast (24h)</span>
					</div>
					<div class="kpi-metric-row font-mono">
						<span class="kpi-val">{totalPvKwh.toFixed(1)}</span>
						<span class="kpi-unit">kWh</span>
					</div>
					<div class="kpi-subtext font-mono">
						Peak: <strong class="text-amber">{peakPvKw.toFixed(1)} kW</strong> • Daylight: <strong>{daylightHoursCount}h</strong>
					</div>
				</div>

				<div class="kpi-box">
					<div class="kpi-label-row">
						<span class="kpi-pip load-pip"></span>
						<span class="kpi-label">Building load demand (24h)</span>
					</div>
					<div class="kpi-metric-row font-mono">
						<span class="kpi-val">{totalLoadKwh.toFixed(1)}</span>
						<span class="kpi-unit">kWh</span>
					</div>
					<div class="kpi-subtext font-mono">
						Peak: <strong class="text-sky">{peakLoadKw.toFixed(1)} kW</strong> • Baseload: <strong>10.0 kW</strong>
					</div>
				</div>

				<div class="kpi-box">
					<div class="kpi-label-row">
						<span class="kpi-pip" class:surplus-pip={netBalanceKwh >= 0} class:deficit-pip={netBalanceKwh < 0}></span>
						<span class="kpi-label">Net battery storage balance</span>
					</div>
					<div class="kpi-metric-row font-mono">
						<span class="kpi-val" class:text-emerald={netBalanceKwh >= 0} class:text-rose={netBalanceKwh < 0}>
							{netBalanceKwh >= 0 ? '+' : ''}{netBalanceKwh.toFixed(1)}
						</span>
						<span class="kpi-unit">kWh</span>
					</div>
					<div class="kpi-subtext font-mono">
						<span class="kpi-badge" class:surplus-badge={netBalanceKwh >= 0} class:deficit-badge={netBalanceKwh < 0}>
							{netBalanceKwh >= 0 ? 'Surplus solar charging' : 'Deficit storage dispatch'}
						</span>
					</div>
				</div>

				<div class="kpi-box">
					<div class="kpi-label-row">
						<span class="kpi-label">Inference latency & SLA</span>
					</div>
					<div class="kpi-metric-row font-mono">
						<span class="kpi-val">{forecastResult.metadata.execution_time_ms.toFixed(1)}</span>
						<span class="kpi-unit">ms</span>
					</div>
					<div class="kpi-subtext font-mono">
						PV nMAE: <strong>0.26%</strong> • Load nMAE: <strong>2.99%</strong>
					</div>
				</div>
			</section>
		{/if}

		<!-- Error Banner -->
		{#if pipelineError}
			<div class="error-banner font-mono">
				<div class="error-content">
					<span class="error-badge">SUPERVISORY FAULT</span>
					<span class="error-message">{pipelineError}</span>
				</div>
				<button class="error-dismiss-btn" onclick={() => (pipelineError = null)}>✕</button>
			</div>
		{/if}

		<!-- Control Console -->
		<section class="controls-panel">
			<div class="controls-row">
				<!-- Origin Time Picker -->
				<div class="control-group">
					<label for="origin-picker" class="control-label">Forecast origin</label>
					<div class="input-and-nudges">
						<input
							id="origin-picker"
							type="datetime-local"
							step="3600"
							class="origin-field font-mono"
							bind:value={customOrigin}
							onchange={() => runPipeline()}
						/>
						<div class="nudge-group font-mono">
							<button class="nudge-btn" onclick={() => adjustOriginHours(-1)} title="Step 1 hour back">
								−1h
							</button>
							<button class="nudge-btn now-btn" onclick={setOriginToNow} title="Set to current hour">
								Now
							</button>
							<button class="nudge-btn" onclick={() => adjustOriginHours(1)} title="Step 1 hour forward">
								+1h
							</button>
						</div>
					</div>
				</div>

				<!-- Dropout Simulator -->
				<div class="control-group">
					<span class="control-label">Telemetry sanitizer stress test</span>
					<div class="dropout-selector font-mono">
						<button
							class="dropout-btn"
							class:active={!injectGap}
							onclick={() => {
								injectGap = false;
								runPipeline();
							}}
						>
							Continuous
						</button>
						<button
							class="dropout-btn"
							class:active={injectGap && gapHours === 2}
							onclick={() => {
								injectGap = true;
								gapHours = 2;
								runPipeline();
							}}
						>
							2h (Heal)
						</button>
						<button
							class="dropout-btn trip-btn"
							class:active={injectGap && gapHours === 4}
							onclick={() => {
								injectGap = true;
								gapHours = 4;
								runPipeline();
							}}
						>
							4h (Trip)
						</button>
					</div>
				</div>

				<!-- Execute Action -->
				<div class="control-group action-group">
					<span class="control-label">&nbsp;</span>
					<button
						class="run-action-btn font-mono"
						disabled={isRunning}
						onclick={() => runPipeline()}
					>
						{#if isRunning}
							<span class="loading-spinner"></span>
							<span>Running...</span>
						{:else}
							<span>Run forecast</span>
							<span class="btn-icon" aria-hidden="true">
								<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"><path d="M4.5 11.5l7-7M5.5 4.5h6v6" /></svg>
							</span>
						{/if}
					</button>
				</div>
			</div>

			<!-- Scenarios Filter Row -->
			<div class="scenarios-row">
				<span class="scenarios-label">Scenario profiles:</span>
				<div class="scenario-buttons font-mono">
					{#each SCENARIO_PRESETS as preset}
						<button
							class="scenario-btn"
							class:active={selectedScenarioId === preset.id}
							onclick={() => loadScenario(preset.id)}
						>
							<span>{preset.name}</span>
							{#if preset.hasGap}
								<span class="badge-mini font-mono">Dropout</span>
							{/if}
						</button>
					{/each}
				</div>
			</div>

			<!-- Preset Info -->
			<div class="scenario-meta">
				<p class="meta-description">{currentPreset.description}</p>
			</div>
		</section>

		<!-- Visual Chart -->
		{#if forecastResult}
			<section class="content-section">
				<ForecastChart
					timestamps={forecastResult.timestamps}
					pvForecast={forecastResult.p_pv_forecast}
					loadForecast={forecastResult.p_load_forecast}
					weather={weatherData}
				/>
			</section>

			<!-- 5-Stage Audit -->
			<section class="content-section">
				<PipelineSteps
					origin={forecastResult.metadata.origin}
					historyCount={historyData.length}
					hasGap={injectGap}
					gapHours={gapHours}
					latencyMs={forecastResult.metadata.execution_time_ms}
					pvForecast={forecastResult.p_pv_forecast}
					loadForecast={forecastResult.p_load_forecast}
					{isLiveBackend}
					source={executionSource}
				/>
			</section>

			<!-- Telemetry & Raw Data Explorer -->
			<section class="content-section">
				<TelemetryDrawer history={historyData} weather={weatherData} />
			</section>
		{/if}
	</div>

	<!-- Info Modal -->
	<InfoModal isOpen={showInfoModal} onClose={() => (showInfoModal = false)} />
</main>

<style>
	.page-viewport {
		width: 100%;
		padding: 1rem 1.5rem 7rem;
		display: flex;
		justify-content: center;
	}

	.page-container {
		width: 100%;
		max-width: 1200px;
		display: flex;
		flex-direction: column;
		gap: 3rem;
	}

	/* Gentle staggered entrance: transform + opacity only */
	@keyframes rise {
		from {
			opacity: 0;
			transform: translateY(18px);
		}
		to {
			opacity: 1;
			transform: none;
		}
	}

	.hero-header,
	.kpi-box,
	.controls-panel,
	.content-section {
		animation: rise 0.9s var(--ease) both;
	}

	.hero-header {
		animation-delay: 0.05s;
	}

	.controls-panel {
		animation-delay: 0.1s;
	}

	.content-section {
		animation-delay: 0.12s;
	}

	.kpi-box:nth-child(2) {
		animation-delay: 0.06s;
	}

	.kpi-box:nth-child(3) {
		animation-delay: 0.12s;
	}

	.kpi-box:nth-child(4) {
		animation-delay: 0.18s;
	}

	/* Floating dark glass-pill nav */
	.app-nav {
		position: sticky;
		top: 14px;
		z-index: 10;
		display: flex;
		justify-content: space-between;
		align-items: center;
		flex-wrap: wrap;
		gap: 0.75rem 1rem;
		padding: 0.45rem 0.45rem 0.45rem 1.4rem;
		border-radius: 999px;
		background: rgba(23, 21, 18, 0.75);
		backdrop-filter: blur(20px) saturate(1.4);
		-webkit-backdrop-filter: blur(20px) saturate(1.4);
		box-shadow:
			0 0 0 1px var(--hairline),
			inset 0 1px 0 rgba(255, 244, 225, 0.08),
			0 18px 36px -16px rgba(0, 0, 0, 0.75);
	}

	.nav-brand {
		display: flex;
		align-items: center;
		gap: 0.7rem;
	}

	.brand-name {
		display: inline-flex;
		align-items: center;
		gap: 0.65rem;
		font-size: 1.05rem;
		font-weight: 600;
		letter-spacing: -0.02em;
		color: var(--text-primary);
	}

	/* The "sun" mark */
	.brand-name::before {
		content: '';
		width: 10px;
		height: 10px;
		border-radius: 50%;
		background: var(--color-pv);
		box-shadow: 0 0 0 4px var(--color-pv-muted);
	}

	.brand-divider {
		color: var(--text-faint);
	}

	.brand-context {
		font-size: 0.85rem;
		color: var(--text-muted);
	}

	.nav-meta {
		display: flex;
		align-items: center;
		gap: 0.9rem;
		font-size: 0.78rem;
		flex-wrap: wrap;
	}

	.ratings-spec {
		color: var(--text-muted);
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding-right: 0.25rem;
	}

	.spec-divider {
		color: var(--text-faint);
	}

	.status-indicator {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		background: var(--surface-sunken);
		color: var(--text-secondary);
		padding: 0.45rem 0.85rem;
		border-radius: 999px;
		font-size: 0.74rem;
		box-shadow: inset 0 0 0 1px var(--hairline);
		transition:
			background-color 0.4s var(--ease),
			color 0.4s var(--ease);
	}

	.status-indicator:hover {
		background: var(--surface-hover);
		color: var(--text-primary);
	}

	.status-dot {
		width: 7px;
		height: 7px;
		border-radius: 50%;
		background: var(--text-faint);
		transition: background-color 0.4s var(--ease);
	}

	.status-indicator.online .status-dot {
		background: var(--color-surplus);
		box-shadow: 0 0 0 3px var(--color-surplus-muted);
	}

	.status-indicator.offline .status-dot {
		background: var(--color-pv);
		box-shadow: 0 0 0 3px var(--color-pv-muted);
	}

	/* Inverted paper CTA with nested icon island */
	.doc-link-btn,
	.run-action-btn {
		display: inline-flex;
		align-items: center;
		background: var(--cta-bg);
		color: var(--cta-fg);
		border-radius: 999px;
		font-weight: 600;
		transition:
			transform 0.5s var(--ease),
			background-color 0.4s var(--ease);
	}

	.doc-link-btn {
		gap: 0.7rem;
		padding: 0.3rem 0.3rem 0.3rem 1.05rem;
		font-size: 0.8rem;
	}

	.btn-icon {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 28px;
		height: 28px;
		border-radius: 50%;
		background: rgba(20, 18, 14, 0.12);
		color: var(--cta-fg);
		transition: transform 0.5s var(--ease);
	}

	.btn-icon svg {
		width: 13px;
		height: 13px;
	}

	.doc-link-btn:hover,
	.run-action-btn:hover:not(:disabled) {
		background: var(--cta-hover);
	}

	.doc-link-btn:hover .btn-icon,
	.run-action-btn:hover:not(:disabled) .btn-icon {
		transform: translate(2px, -1px) scale(1.06);
	}

	.doc-link-btn:active,
	.run-action-btn:active:not(:disabled) {
		transform: scale(0.98);
	}

	/* Hero */
	.hero-header {
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
		padding: 3.5rem 0 0.5rem;
	}

	.hero-title {
		margin: 0;
		max-width: 1040px;
		font-family: var(--font-display);
		font-size: clamp(2.3rem, 5.2vw, 4.4rem);
		font-weight: 400;
		line-height: 1.03;
		letter-spacing: -0.025em;
		color: var(--text-primary);
		text-wrap: balance;
	}

	.hero-title em {
		font-style: italic;
		color: var(--color-pv-ink);
	}

	.hero-description {
		margin: 0;
		max-width: 620px;
		font-size: 1.05rem;
		line-height: 1.6;
		color: var(--text-secondary);
	}

	/* KPI cards */
	.kpi-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
		gap: 1.5rem;
	}

	.kpi-box {
		background: var(--surface);
		border-radius: var(--radius-core);
		box-shadow: var(--bezel);
		padding: 1.4rem 1.5rem 1.35rem;
		display: flex;
		flex-direction: column;
		gap: 0.7rem;
	}

	.kpi-label-row {
		display: flex;
		align-items: center;
		gap: 0.6rem;
		min-height: 1rem;
	}

	.kpi-label {
		font-size: 0.8rem;
		font-weight: 500;
		color: var(--text-secondary);
	}

	.kpi-pip {
		width: 7px;
		height: 7px;
		border-radius: 50%;
	}

	.pv-pip {
		background: var(--color-pv);
		box-shadow: 0 0 0 3px var(--color-pv-muted);
	}

	.load-pip {
		background: var(--color-load);
		box-shadow: 0 0 0 3px var(--color-load-muted);
	}

	.surplus-pip {
		background: var(--color-surplus);
		box-shadow: 0 0 0 3px var(--color-surplus-muted);
	}

	.deficit-pip {
		background: var(--color-deficit);
		box-shadow: 0 0 0 3px var(--color-deficit-muted);
	}

	.kpi-metric-row {
		display: flex;
		align-items: baseline;
		gap: 0.45rem;
		font-family: var(--font-sans);
	}

	.kpi-val {
		font-family: var(--font-display);
		font-size: 3.1rem;
		font-weight: 400;
		line-height: 0.95;
		letter-spacing: -0.02em;
		color: var(--text-primary);
	}

	.kpi-unit {
		font-size: 0.85rem;
		font-weight: 500;
		color: var(--text-muted);
	}

	.kpi-subtext {
		font-family: var(--font-sans);
		font-size: 0.76rem;
		color: var(--text-muted);
		padding-top: 0.75rem;
		margin-top: 0.15rem;
		border-top: 1px solid var(--hairline);
	}

	.kpi-subtext strong {
		color: var(--text-primary);
		font-weight: 500;
	}

	.text-amber {
		color: var(--color-pv-ink) !important;
	}

	.text-sky {
		color: var(--color-load-ink) !important;
	}

	.text-emerald {
		color: var(--color-surplus-ink) !important;
	}

	.text-rose {
		color: var(--color-deficit-ink) !important;
	}

	.kpi-badge {
		display: inline-flex;
		align-items: center;
		padding: 0.2rem 0.65rem;
		border-radius: 999px;
		font-size: 0.72rem;
		font-weight: 500;
	}

	.kpi-badge.surplus-badge {
		color: var(--color-surplus-ink);
		background: var(--color-surplus-muted);
	}

	.kpi-badge.deficit-badge {
		color: var(--color-deficit-ink);
		background: var(--color-deficit-muted);
	}

	/* Controls console */
	.controls-panel {
		background: var(--surface);
		border-radius: var(--radius-core);
		box-shadow: var(--bezel);
		padding: 1.75rem 2rem;
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
	}

	.controls-row {
		display: flex;
		align-items: flex-end;
		justify-content: space-between;
		gap: 1.5rem 2rem;
		flex-wrap: wrap;
	}

	.control-group {
		display: flex;
		flex-direction: column;
		gap: 0.6rem;
	}

	.control-label {
		font-size: 0.68rem;
		font-weight: 500;
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: var(--text-muted);
	}

	.input-and-nudges {
		display: flex;
		align-items: center;
		gap: 0.6rem;
		flex-wrap: wrap;
	}

	.origin-field {
		background: var(--surface-sunken);
		border: none;
		border-radius: 12px;
		box-shadow: inset 0 0 0 1px var(--hairline);
		color: var(--text-primary);
		padding: 0.62rem 0.9rem;
		font-size: 0.82rem;
		transition: box-shadow 0.4s var(--ease);
	}

	.origin-field:hover {
		box-shadow: inset 0 0 0 1px var(--hairline-strong);
	}

	/* Segmented tracks: nudges + dropout selector */
	.nudge-group,
	.dropout-selector {
		display: inline-flex;
		background: var(--surface-sunken);
		border-radius: 999px;
		padding: 3px;
		gap: 2px;
	}

	.nudge-btn,
	.dropout-btn {
		font-family: var(--font-sans);
		background: transparent;
		color: var(--text-secondary);
		border-radius: 999px;
		font-size: 0.78rem;
		font-weight: 500;
		transition:
			background-color 0.4s var(--ease),
			color 0.4s var(--ease),
			box-shadow 0.4s var(--ease);
	}

	.nudge-btn {
		padding: 0.45rem 0.8rem;
	}

	.dropout-btn {
		padding: 0.45rem 0.95rem;
	}

	.nudge-btn:hover,
	.dropout-btn:hover {
		color: var(--text-primary);
	}

	.now-btn {
		color: var(--text-primary);
	}

	.dropout-btn.active {
		background: var(--surface);
		color: var(--text-primary);
		box-shadow:
			0 0 0 1px var(--hairline),
			0 2px 6px -2px rgba(23, 21, 15, 0.16);
	}

	.dropout-btn.trip-btn.active {
		background: var(--color-deficit-muted);
		color: var(--color-deficit-ink);
		box-shadow: 0 0 0 1px rgba(224, 54, 95, 0.28);
	}

	.action-group {
		margin-left: auto;
	}

	.run-action-btn {
		gap: 1rem;
		padding: 0.4rem 0.4rem 0.4rem 1.5rem;
		font-size: 0.9rem;
	}

	.run-action-btn .btn-icon {
		width: 34px;
		height: 34px;
	}

	.run-action-btn .btn-icon svg {
		width: 15px;
		height: 15px;
	}

	.run-action-btn:disabled {
		opacity: 0.6;
		padding-right: 1.5rem;
		padding-block: 0.8rem;
	}

	.loading-spinner {
		width: 14px;
		height: 14px;
		border: 2px solid rgba(20, 18, 14, 0.28);
		border-top-color: var(--cta-fg);
		border-radius: 50%;
		animation: spin 0.7s linear infinite;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	/* Scenarios */
	.scenarios-row {
		display: flex;
		align-items: center;
		gap: 0.75rem 1.25rem;
		padding-top: 1.5rem;
		border-top: 1px solid var(--hairline);
		flex-wrap: wrap;
	}

	.scenarios-label {
		font-size: 0.8rem;
		color: var(--text-muted);
	}

	.scenario-buttons {
		display: flex;
		gap: 0.5rem;
		flex-wrap: wrap;
	}

	.scenario-btn {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		font-family: var(--font-sans);
		background: var(--surface-sunken);
		color: var(--text-secondary);
		border-radius: 999px;
		padding: 0.5rem 1rem;
		font-size: 0.82rem;
		font-weight: 500;
		box-shadow: inset 0 0 0 1px var(--hairline);
		transition:
			background-color 0.4s var(--ease),
			color 0.4s var(--ease),
			transform 0.5s var(--ease);
	}

	.scenario-btn:hover {
		background: var(--surface-hover);
		color: var(--text-primary);
	}

	.scenario-btn:active {
		transform: scale(0.98);
	}

	.scenario-btn.active {
		background: var(--cta-bg);
		color: var(--cta-fg);
		box-shadow: none;
	}

	.badge-mini {
		font-family: var(--font-sans);
		font-size: 0.66rem;
		font-weight: 500;
		padding: 0.12rem 0.5rem;
		border-radius: 999px;
		background: rgba(255, 244, 225, 0.08);
		color: var(--text-secondary);
	}

	.scenario-btn.active .badge-mini {
		background: rgba(20, 18, 14, 0.14);
		color: var(--cta-fg);
	}

	.scenario-meta {
		font-size: 0.85rem;
		color: var(--text-secondary);
	}

	.meta-description {
		margin: 0;
		line-height: 1.55;
		max-width: 72ch;
	}

	/* Error banner */
	.error-banner {
		background: var(--color-deficit-muted);
		box-shadow: 0 0 0 1px rgba(255, 92, 130, 0.25);
		border-radius: 16px;
		padding: 0.9rem 1rem 0.9rem 1.25rem;
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 1rem;
	}

	.error-content {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		font-size: 0.8rem;
		flex-wrap: wrap;
	}

	.error-badge {
		background: var(--color-deficit-ink);
		color: #14120e;
		font-family: var(--font-sans);
		font-size: 0.64rem;
		font-weight: 700;
		padding: 0.22rem 0.6rem;
		border-radius: 999px;
		letter-spacing: 0.08em;
	}

	.error-message {
		color: var(--color-deficit-ink);
		line-height: 1.45;
	}

	.error-dismiss-btn {
		width: 28px;
		height: 28px;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		border-radius: 50%;
		background: rgba(255, 92, 130, 0.16);
		color: var(--color-deficit-ink);
		font-size: 0.75rem;
		transition:
			background-color 0.4s var(--ease),
			transform 0.5s var(--ease);
	}

	.error-dismiss-btn:hover {
		background: rgba(255, 92, 130, 0.3);
	}

	.error-dismiss-btn:active {
		transform: scale(0.94);
	}

	.content-section {
		width: 100%;
	}

	@media (max-width: 760px) {
		.page-viewport {
			padding: 0.75rem 1.25rem 5rem;
		}

		.page-container {
			gap: 2.5rem;
		}

		.app-nav {
			position: static;
			border-radius: 28px;
			padding: 0.9rem 1rem;
		}

		.hero-header {
			padding-top: 1.5rem;
		}

		.controls-panel {
			padding: 1.35rem 1.25rem;
		}

		.action-group {
			margin-left: 0;
		}
	}
</style>

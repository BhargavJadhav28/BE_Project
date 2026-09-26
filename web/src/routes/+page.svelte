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
						<span>API :8000 online</span>
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
					Architecture guide
				</button>
			</div>
		</nav>

		<!-- Hero Section -->
		<header class="hero-header">
			<h1 class="hero-title">
				24-hour solar generation, building load forecasting & battery dispatch
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
		padding: 2.5rem 1.5rem 6rem;
		display: flex;
		justify-content: center;
		background: #000000;
	}

	.page-container {
		width: 100%;
		max-width: 1200px;
		display: flex;
		flex-direction: column;
		gap: 2.25rem;
	}

	/* Minimal Nav */
	.app-nav {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding-bottom: 1.5rem;
		border-bottom: 1px solid #1C1C24;
		flex-wrap: wrap;
		gap: 1rem;
	}

	.nav-brand {
		display: flex;
		align-items: center;
		gap: 0.65rem;
	}

	.brand-name {
		font-size: 1.1rem;
		font-weight: 700;
		color: #FFFFFF;
		letter-spacing: -0.02em;
	}

	.brand-divider {
		color: #3F3F46;
	}

	.brand-context {
		font-size: 0.85rem;
		color: #A1A1AA;
	}

	.nav-meta {
		display: flex;
		align-items: center;
		gap: 1.25rem;
		font-size: 0.8rem;
		flex-wrap: wrap;
	}

	.ratings-spec {
		color: #71717A;
		display: flex;
		align-items: center;
		gap: 0.45rem;
	}

	.spec-divider {
		color: #27272A;
	}

	.status-indicator {
		display: flex;
		align-items: center;
		gap: 0.45rem;
		background: #09090C;
		color: #A1A1AA;
		padding: 0.35rem 0.75rem;
		border-radius: 6px;
		border: 1px solid #1C1C24;
		cursor: pointer;
		transition: all 0.15s ease;
	}

	.status-indicator:hover {
		border-color: #3F3F46;
		color: #FFFFFF;
	}

	.status-dot {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		background: #52525B;
	}

	.status-indicator.online .status-dot {
		background: #FFFFFF;
		box-shadow: 0 0 6px rgba(255, 255, 255, 0.6);
	}

	.status-indicator.offline .status-dot {
		background: #71717A;
	}

	.doc-link-btn {
		background: #141418;
		color: #FFFFFF;
		padding: 0.35rem 0.85rem;
		font-size: 0.8rem;
		font-weight: 500;
		border-radius: 6px;
		border: 1px solid #27272A;
		cursor: pointer;
		transition: all 0.15s ease;
	}

	.doc-link-btn:hover {
		border-color: #3F3F46;
		background: #1C1C22;
	}

	/* Hero */
	.hero-header {
		display: flex;
		flex-direction: column;
		gap: 0.65rem;
		padding: 0.5rem 0;
	}

	.hero-title {
		margin: 0;
		font-size: clamp(1.85rem, 3.2vw, 2.5rem);
		font-weight: 600;
		line-height: 1.2;
		letter-spacing: -0.03em;
		color: #FFFFFF;
		max-width: 920px;
	}

	.hero-description {
		margin: 0;
		font-size: 1rem;
		line-height: 1.5;
		color: #A1A1AA;
		max-width: 780px;
	}

	/* KPI Grid */
	.kpi-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
		gap: 1rem;
	}

	.kpi-box {
		background: #09090C;
		border: 1px solid #1C1C24;
		border-radius: 8px;
		padding: 1.25rem 1.5rem;
		display: flex;
		flex-direction: column;
		gap: 0.45rem;
		transition: border-color 0.15s ease;
	}

	.kpi-box:hover {
		border-color: #2E2E38;
	}

	.kpi-label {
		font-size: 0.8rem;
		color: #71717A;
	}

	.kpi-metric-row {
		display: flex;
		align-items: baseline;
		gap: 0.4rem;
	}

	.kpi-val {
		font-size: 1.85rem;
		font-weight: 600;
		color: #FFFFFF;
		line-height: 1;
		letter-spacing: -0.02em;
	}


	.kpi-unit {
		font-size: 0.85rem;
		color: #52525B;
	}

	.kpi-label-row {
		display: flex;
		align-items: center;
		gap: 0.45rem;
	}

	.kpi-pip {
		width: 6px;
		height: 6px;
		border-radius: 50%;
	}

	.pv-pip {
		background: #F59E0B;
	}

	.load-pip {
		background: #38BDF8;
	}

	.surplus-pip {
		background: #10B981;
	}

	.deficit-pip {
		background: #F43F5E;
	}

	.kpi-subtext {
		font-size: 0.75rem;
		color: #71717A;
		margin-top: 0.2rem;
	}

	.kpi-subtext strong {
		color: #FFFFFF;
	}

	.text-amber {
		color: #F59E0B !important;
	}

	.text-sky {
		color: #38BDF8 !important;
	}

	.text-emerald {
		color: #10B981 !important;
	}

	.text-rose {
		color: #F43F5E !important;
	}

	.kpi-badge {
		display: inline-flex;
		align-items: center;
		padding: 0.12rem 0.45rem;
		border-radius: 4px;
		font-size: 0.7rem;
		font-weight: 500;
	}

	.kpi-badge.surplus-badge {
		color: #10B981;
		background: rgba(16, 185, 129, 0.12);
		border: 1px solid rgba(16, 185, 129, 0.25);
	}

	.kpi-badge.deficit-badge {
		color: #F43F5E;
		background: rgba(244, 63, 94, 0.12);
		border: 1px solid rgba(244, 63, 94, 0.25);
	}

	/* Controls Panel */
	.controls-panel {
		background: #09090C;
		border: 1px solid #1C1C24;
		border-radius: 8px;
		padding: 1.5rem 1.75rem;
		display: flex;
		flex-direction: column;
		gap: 1.25rem;
	}

	.controls-row {
		display: flex;
		align-items: flex-end;
		justify-content: space-between;
		gap: 1.5rem;
		flex-wrap: wrap;
	}

	.control-group {
		display: flex;
		flex-direction: column;
		gap: 0.45rem;
	}

	.control-label {
		font-size: 0.775rem;
		color: #71717A;
		font-weight: 500;
	}

	.input-and-nudges {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.origin-field {
		background: #050507;
		border: 1px solid #1C1C24;
		border-radius: 6px;
		color: #FFFFFF;
		padding: 0.5rem 0.75rem;
		font-size: 0.8rem;
		outline: none;
		transition: border-color 0.15s ease;
	}

	.origin-field:focus {
		border-color: #52525B;
	}

	.nudge-group {
		display: flex;
		background: #050507;
		border: 1px solid #1C1C24;
		border-radius: 6px;
		overflow: hidden;
	}

	.nudge-btn {
		background: transparent;
		color: #A1A1AA;
		padding: 0.5rem 0.65rem;
		font-size: 0.725rem;
		cursor: pointer;
		transition: all 0.15s ease;
	}

	.nudge-btn:hover {
		background: #141418;
		color: #FFFFFF;
	}

	.now-btn {
		color: #FFFFFF;
		font-weight: 600;
	}

	/* Error Banner */
	.error-banner {
		background: rgba(244, 63, 94, 0.08);
		border: 1px solid rgba(244, 63, 94, 0.35);
		border-radius: 8px;
		padding: 0.85rem 1.25rem;
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 1rem;
		color: #FFFFFF;
	}

	.error-content {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		font-size: 0.775rem;
		flex-wrap: wrap;
	}

	.error-badge {
		background: #F43F5E;
		color: #FFFFFF;
		font-size: 0.65rem;
		font-weight: 700;
		padding: 0.15rem 0.45rem;
		border-radius: 3px;
		letter-spacing: 0.02em;
	}

	.error-message {
		color: #FDA4AF;
		line-height: 1.4;
	}

	.error-dismiss-btn {
		background: transparent;
		color: #A1A1AA;
		border: 1px solid rgba(244, 63, 94, 0.3);
		border-radius: 4px;
		padding: 0.2rem 0.5rem;
		font-size: 0.75rem;
		cursor: pointer;
		transition: all 0.15s ease;
	}

	.error-dismiss-btn:hover {
		color: #FFFFFF;
		background: rgba(244, 63, 94, 0.2);
	}

	/* Segmented Dropout Selector */
	.dropout-selector {
		display: flex;
		background: #050507;
		border: 1px solid #1C1C24;
		border-radius: 6px;
		padding: 2px;
		gap: 2px;
	}

	.dropout-btn {
		background: transparent;
		color: #71717A;
		padding: 0.38rem 0.75rem;
		font-size: 0.75rem;
		font-weight: 500;
		border-radius: 4px;
		cursor: pointer;
		transition: all 0.15s ease;
	}

	.dropout-btn:hover {
		color: #FFFFFF;
	}

	.dropout-btn.active {
		background: #1C1C24;
		color: #FFFFFF;
		font-weight: 600;
	}

	.dropout-btn.trip-btn.active {
		background: rgba(244, 63, 94, 0.15);
		color: #F43F5E;
		border: 1px solid rgba(244, 63, 94, 0.3);
	}

	.action-group {
		margin-left: auto;
	}

	.run-action-btn {
		background: #FFFFFF;
		color: #000000;
		border-radius: 6px;
		padding: 0.55rem 1.4rem;
		font-size: 0.85rem;
		font-weight: 600;
		display: flex;
		align-items: center;
		gap: 0.5rem;
		cursor: pointer;
		transition: all 0.15s ease;
	}

	.run-action-btn:hover:not(:disabled) {
		background: #E4E4E7;
		transform: translateY(-1px);
		box-shadow: 0 4px 12px rgba(255, 255, 255, 0.1);
	}

	.run-action-btn:disabled {
		opacity: 0.45;
		cursor: not-allowed;
	}

	.loading-spinner {
		width: 14px;
		height: 14px;
		border: 2px solid rgba(0, 0, 0, 0.2);
		border-top-color: #000000;
		border-radius: 50%;
		animation: spin 0.6s linear infinite;
	}

	@keyframes spin {
		to { transform: rotate(360deg); }
	}

	/* Scenarios */
	.scenarios-row {
		display: flex;
		align-items: center;
		gap: 1rem;
		padding-top: 1rem;
		border-top: 1px solid #1C1C24;
		flex-wrap: wrap;
	}

	.scenarios-label {
		font-size: 0.8rem;
		color: #71717A;
	}

	.scenario-buttons {
		display: flex;
		gap: 0.5rem;
		flex-wrap: wrap;
	}

	.scenario-btn {
		background: #050507;
		border: 1px solid #1C1C24;
		border-radius: 6px;
		color: #A1A1AA;
		padding: 0.4rem 0.85rem;
		font-size: 0.8rem;
		font-weight: 500;
		display: flex;
		align-items: center;
		gap: 0.45rem;
		cursor: pointer;
		transition: all 0.15s ease;
	}

	.scenario-btn:hover {
		color: #FFFFFF;
		border-color: #2E2E38;
	}

	.scenario-btn.active {
		background: #1C1C24;
		border-color: #52525B;
		color: #FFFFFF;
	}

	.badge-mini {
		font-size: 0.65rem;
		padding: 0.1rem 0.35rem;
		border-radius: 3px;
		background: #141418;
		color: #D4D4D8;
		border: 1px solid #27272A;
	}

	.scenario-meta {
		font-size: 0.8rem;
		color: #71717A;
	}

	.meta-description {
		margin: 0;
		line-height: 1.45;
	}

	.content-section {
		width: 100%;
	}
</style>

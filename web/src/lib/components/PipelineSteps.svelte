<script lang="ts">
	import {
		ShieldCheck,
		Lock,
		Cpu,
		SlidersHorizontal,
		BatteryCharging,
		ArrowRight,
		ArrowDown,
		X,
		CheckCircle2,
		AlertTriangle,
		TrendingUp,
		RotateCcw,
		Calendar,
		Layers
	} from '@lucide/svelte';

	interface Props {
		origin: string;
		historyCount: number;
		hasGap: boolean;
		gapHours: number;
		latencyMs: number;
		pvForecast: number[];
		loadForecast: number[];
		isLiveBackend: boolean;
		source: string;
	}

	let {
		origin = '',
		historyCount = 49,
		hasGap = false,
		gapHours = 0,
		latencyMs = 0,
		pvForecast = [],
		loadForecast = [],
		isLiveBackend = false,
		source = ''
	}: Props = $props();

	type StageId = 'sanitizer' | 'conditioning' | 'inference' | 'guard' | 'dispatch';
	let activeStage = $state<StageId | null>('sanitizer');
	let showTechSpecs = $state(false);

	function selectStage(id: StageId) {
		activeStage = activeStage === id ? null : id;
	}

	let totalPvKwh = $derived(pvForecast.reduce((acc, val) => acc + val, 0));
	let totalLoadKwh = $derived(loadForecast.reduce((acc, val) => acc + val, 0));
	let netBalanceKwh = $derived(totalPvKwh - totalLoadKwh);
	let peakPvKw = $derived(pvForecast.length ? Math.max(...pvForecast) : 0);
	let peakLoadKw = $derived(loadForecast.length ? Math.max(...loadForecast) : 0);

	let solarCoveragePct = $derived(
		totalLoadKwh > 0 ? Math.min(100, Math.round((totalPvKwh / totalLoadKwh) * 100)) : 100
	);

	let originTime = $derived(
		origin
			? origin.includes('T')
				? origin.split('T')[1].slice(0, 5)
				: origin.includes(' ')
					? origin.split(' ')[1].slice(0, 5)
					: origin.slice(11, 16) || origin
			: '—'
	);
</script>

<div class="pipeline-panel">
	<!-- Header -->
	<div class="pipeline-header">
		<div>
			<h2 class="pipeline-title">Execution pipeline & architecture audit</h2>
			<p class="pipeline-subtitle">
				Deterministic 5-stage transformation from raw sensor readings to battery dispatch
			</p>
		</div>

		<div class="pipeline-meta font-mono">
			<button 
				class="mode-toggle-btn"
				class:active={showTechSpecs}
				onclick={() => (showTechSpecs = !showTechSpecs)}
				title="Toggle between ASD-STE100 operational rules and low-level code/math specifications"
			>
				{showTechSpecs ? 'Show simple rules' : 'Show technical specs'}
			</button>
			<span class="source-tag" class:live={isLiveBackend}>
				{isLiveBackend ? 'FastAPI :8000' : 'Simulation'}
			</span>
			<span class="latency-tag">{latencyMs.toFixed(1)} ms</span>
		</div>
	</div>

	<!-- Dataflow Ribbon -->
	<div class="dataflow-ribbon font-mono">
		<button 
			class="flow-node" 
			class:active={activeStage === 'sanitizer'}
			onclick={() => selectStage('sanitizer')}
		>
			<ShieldCheck size={14} class="node-icon" />
			<span>01 Clean Sensor Data</span>
		</button>
		<ArrowRight size={13} class="flow-arrow" />
		
		<button 
			class="flow-node" 
			class:active={activeStage === 'conditioning'}
			onclick={() => selectStage('conditioning')}
		>
			<Lock size={13} class="node-icon" />
			<span>02 Time Anchor & Context</span>
		</button>
		<ArrowRight size={13} class="flow-arrow" />

		<button 
			class="flow-node" 
			class:active={activeStage === 'inference'}
			onclick={() => selectStage('inference')}
		>
			<Cpu size={14} class="node-icon" />
			<span>03 Predict Power</span>
		</button>
		<ArrowRight size={13} class="flow-arrow" />

		<button 
			class="flow-node" 
			class:active={activeStage === 'guard'}
			onclick={() => selectStage('guard')}
		>
			<SlidersHorizontal size={14} class="node-icon" />
			<span>04 Enforce Limits</span>
		</button>
		<ArrowRight size={13} class="flow-arrow" />

		<button 
			class="flow-node" 
			class:active={activeStage === 'dispatch'}
			onclick={() => selectStage('dispatch')}
		>
			<BatteryCharging size={14} class="node-icon" />
			<span>05 Schedule Battery</span>
		</button>
	</div>

	<!-- The 5 Stage Cards Grid: Balanced, Equal-Height Row -->
	<div class="stages-overview-grid">
		<!-- Card 01: Sanitizer -->
		<button 
			class="stage-card" 
			class:selected={activeStage === 'sanitizer'}
			onclick={() => selectStage('sanitizer')}
		>
			<div class="card-head">
				<div class="stage-num-badge font-mono">01</div>
				<div class="stage-label-group">
					<h3 class="stage-card-title">Clean sensor data</h3>
					<span class="stage-card-sub">Self-healing history buffer</span>
				</div>
			</div>

			<div class="card-stats font-mono">
				<div class="card-stat-row">
					<span class="stat-lbl">Buffer</span>
					<span class="stat-num">{historyCount}h contiguous</span>
				</div>
				<div class="card-stat-row">
					<span class="stat-lbl">Feed</span>
					<span class="stat-badge" class:healed={hasGap}>
						{hasGap ? `${gapHours}h filled (Healed)` : 'Continuous stream'}
					</span>
				</div>
			</div>

			<div class="card-footer font-mono">
				<span class="action-hint">{activeStage === 'sanitizer' ? 'Close detail' : 'Inspect stage'}</span>
			</div>
		</button>

		<!-- Card 02: Time Anchor & History -->
		<button 
			class="stage-card" 
			class:selected={activeStage === 'conditioning'}
			onclick={() => selectStage('conditioning')}
		>
			<div class="card-head">
				<div class="stage-num-badge font-mono">02</div>
				<div class="stage-label-group">
					<h3 class="stage-card-title">Time anchor & history</h3>
					<span class="stage-card-sub">Lock origin T & weather context</span>
				</div>
			</div>

			<div class="card-stats font-mono">
				<div class="card-stat-row">
					<span class="stat-lbl">Origin T</span>
					<span class="stat-num">{originTime} (Locked)</span>
				</div>
				<div class="card-stat-row">
					<span class="stat-lbl">Past memory</span>
					<span class="stat-badge anchor-badge">T-24h & T-1h lags</span>
				</div>
			</div>

			<div class="card-footer font-mono">
				<span class="action-hint">{activeStage === 'conditioning' ? 'Close detail' : 'Inspect stage'}</span>
			</div>
		</button>

		<!-- Card 03: Parallel LightGBM -->
		<button 
			class="stage-card" 
			class:selected={activeStage === 'inference'}
			onclick={() => selectStage('inference')}
		>
			<div class="card-head">
				<div class="stage-num-badge font-mono">03</div>
				<div class="stage-label-group">
					<h3 class="stage-card-title">Predict power</h3>
					<span class="stage-card-sub">Dual LightGBM models</span>
				</div>
			</div>

			<div class="card-stats font-mono">
				<div class="card-stat-row">
					<span class="stat-lbl">Speed</span>
					<span class="stat-num highlight">{latencyMs.toFixed(1)} ms</span>
				</div>
				<div class="card-stat-row">
					<span class="stat-lbl">Raw peaks</span>
					<span class="stat-num">{peakPvKw.toFixed(0)} kW / {peakLoadKw.toFixed(0)} kW</span>
				</div>
			</div>

			<div class="card-footer font-mono">
				<span class="action-hint">{activeStage === 'inference' ? 'Close detail' : 'Inspect stage'}</span>
			</div>
		</button>

		<!-- Card 04: Physical Limits -->
		<button 
			class="stage-card" 
			class:selected={activeStage === 'guard'}
			onclick={() => selectStage('guard')}
		>
			<div class="card-head">
				<div class="stage-num-badge font-mono">04</div>
				<div class="stage-label-group">
					<h3 class="stage-card-title">Enforce limits</h3>
					<span class="stage-card-sub">Inverter ceiling & night bounds</span>
				</div>
			</div>

			<div class="card-stats font-mono">
				<div class="card-stat-row">
					<span class="stat-lbl">Night rule</span>
					<span class="stat-badge">0.0 kW (GHI ≤ 0)</span>
				</div>
				<div class="card-stat-row">
					<span class="stat-lbl">Inverter cap</span>
					<span class="stat-num">50.0 kW max</span>
				</div>
			</div>

			<div class="card-footer font-mono">
				<span class="action-hint">{activeStage === 'guard' ? 'Close detail' : 'Inspect stage'}</span>
			</div>
		</button>

		<!-- Card 05: Battery Dispatch -->
		<button 
			class="stage-card" 
			class:selected={activeStage === 'dispatch'}
			onclick={() => selectStage('dispatch')}
		>
			<div class="card-head">
				<div class="stage-num-badge font-mono">05</div>
				<div class="stage-label-group">
					<h3 class="stage-card-title">Schedule battery</h3>
					<span class="stage-card-sub">Energy balance & arbitrage</span>
				</div>
			</div>

			<div class="card-stats font-mono">
				<!-- Split Energy Meter -->
				<div class="mini-energy-bar" title="{solarCoveragePct}% Solar coverage">
					<div class="energy-chunk pv-chunk" style="width: {solarCoveragePct}%;"></div>
					<div class="energy-chunk load-chunk" style="width: {100 - solarCoveragePct}%;"></div>
				</div>

				<div class="card-stat-row">
					<span class="stat-lbl">24h Net</span>
					<span class="stat-num" class:surplus={netBalanceKwh >= 0} class:deficit={netBalanceKwh < 0}>
						{netBalanceKwh >= 0 ? '+' : ''}{netBalanceKwh.toFixed(1)} kWh
					</span>
				</div>
			</div>

			<div class="card-footer font-mono">
				<span class="action-hint">{activeStage === 'dispatch' ? 'Close detail' : 'Inspect stage'}</span>
			</div>
		</button>
	</div>

	<!-- Wide, Full-Width Detail Inspector Panel -->
	{#if activeStage !== null}
		<section class="wide-inspector-panel">
			<!-- Detail Header -->
			<div class="inspector-header">
				<div class="inspector-title-group">
					<div class="inspector-icon-pill">
						{#if activeStage === 'sanitizer'}
							<ShieldCheck size={18} class="text-amber" />
						{:else if activeStage === 'conditioning'}
							<Lock size={18} class="text-sky" />
						{:else if activeStage === 'inference'}
							<Cpu size={18} class="text-amber" />
						{:else if activeStage === 'guard'}
							<SlidersHorizontal size={18} class="text-emerald" />
						{:else if activeStage === 'dispatch'}
							<BatteryCharging size={18} class="text-emerald" />
						{/if}
					</div>
					<div>
						<div class="inspector-badge-row font-mono">
							<span class="stage-tag">STAGE {activeStage === 'sanitizer' ? '01' : activeStage === 'conditioning' ? '02' : activeStage === 'inference' ? '03' : activeStage === 'guard' ? '04' : '05'}</span>
							<span class="spec-mode-badge">{showTechSpecs ? 'Technical Specification' : 'Operational Rules (ASD-STE100)'}</span>
						</div>
						<h3 class="inspector-title">
							{#if activeStage === 'sanitizer'}
								Stage 01: Clean Sensor Data & Lookback Buffer Healing
							{:else if activeStage === 'conditioning'}
								Stage 02: Time Anchor & Sensor History Memory
							{:else if activeStage === 'inference'}
								Stage 03: Parallel Power Prediction via Dual LightGBM
							{:else if activeStage === 'guard'}
								Stage 04: Enforce Physical Microgrid Limits & Night Rules
							{:else if activeStage === 'dispatch'}
								Stage 05: Calculate Energy Balance & Schedule Battery Storage
							{/if}
						</h3>
					</div>
				</div>

				<button class="close-inspector-btn" onclick={() => (activeStage = null)} title="Close detail drawer">
					<X size={16} />
					<span class="font-mono">Close</span>
				</button>
			</div>

			<!-- Spacious 2-Column Body -->
			<div class="inspector-body-grid">
				<!-- Left Column: Plain Operational Rules (ASD-STE100) or Technical Specs -->
				<div class="inspector-col">
					<h4 class="col-heading font-mono">
						<span>{showTechSpecs ? 'LOW-LEVEL CODE IMPLEMENTATION' : 'EXPLICIT OPERATIONAL RULES'}</span>
					</h4>

					{#if !showTechSpecs}
						<div class="rules-list">
							{#if activeStage === 'sanitizer'}
								<div class="rule-card">
									<div class="rule-icon"><CheckCircle2 size={15} class="text-amber" /></div>
									<div class="rule-content">
										<strong>Collect 48 Hours of Sensor History</strong>
										<p>The system ingests 48 continuous hourly readings before forecast origin time T to establish stable baselines.</p>
									</div>
								</div>
								<div class="rule-card">
									<div class="rule-icon"><CheckCircle2 size={15} class="text-emerald" /></div>
									<div class="rule-content">
										<strong>Automatic Healing (Gaps ≤ 3 Hours)</strong>
										<p>If sensor packet loss creates gaps of 3 hours or less, the sanitizer calculates missing values automatically via linear interpolation.</p>
									</div>
								</div>
								<div class="rule-card">
									<div class="rule-icon"><AlertTriangle size={15} class="text-rose" /></div>
									<div class="rule-content">
										<strong>Supervisory Trip Alarm (Gaps &gt; 3 Hours)</strong>
										<p>If sensor blackouts exceed 3 hours, interpolation is unsafe. The pipeline stops and signals a supervisory alert for fail-safe fallback dispatch.</p>
									</div>
								</div>
								<div class="rule-card">
									<div class="rule-icon"><CheckCircle2 size={15} class="text-amber" /></div>
									<div class="rule-content">
										<strong>Nocturnal Zero-Fill</strong>
										<p>Missing solar generation values during night hours (solar irradiance = 0) are strictly forced to 0.0 kW.</p>
									</div>
								</div>

							{:else if activeStage === 'conditioning'}
								<div class="rule-card">
									<div class="rule-icon"><Lock size={15} class="text-sky" /></div>
									<div class="rule-content">
										<strong>Origin Lock at Time T (Zero Data Leakage)</strong>
										<p>All historical sensor readings lock at hour T. The model cannot read future sensor data when calculating predictions.</p>
									</div>
								</div>
								<div class="rule-card">
									<div class="rule-icon"><RotateCcw size={15} class="text-sky" /></div>
									<div class="rule-content">
										<strong>Use Yesterday's Baseline (T-24h Lag)</strong>
										<p>Electrical demand repeats daily. The reading from 24 hours ago gives the model its primary reference baseline for today.</p>
									</div>
								</div>
								<div class="rule-card">
									<div class="rule-icon"><TrendingUp size={15} class="text-sky" /></div>
									<div class="rule-content">
										<strong>Use Immediate Momentum (T-1h Lag)</strong>
										<p>The reading from 1 hour ago tells the model whether building electrical consumption is currently ramping up or ramping down.</p>
									</div>
								</div>
								<div class="rule-card">
									<div class="rule-icon"><CheckCircle2 size={15} class="text-emerald" /></div>
									<div class="rule-content">
										<strong>Add Forward Numerical Weather Predictions</strong>
										<p>Combines locked historical readings with 24-hour forward forecasts for solar irradiance, ambient temperature, and cloud cover.</p>
									</div>
								</div>

							{:else if activeStage === 'inference'}
								<div class="rule-card">
									<div class="rule-icon"><Cpu size={15} class="text-amber" /></div>
									<div class="rule-content">
										<strong>Run Dual Gradient-Boosted Models in Parallel</strong>
										<p>Two specialized LightGBM regressors execute simultaneously: one model predicts Solar PV and one model predicts Building Load.</p>
									</div>
								</div>
								<div class="rule-card">
									<div class="rule-icon"><CheckCircle2 size={15} class="text-amber" /></div>
									<div class="rule-content">
										<strong>Predict All 24 Future Hours Simultaneously</strong>
										<p>Instead of feeding predictions back recursively, both models condition directly on the step number (h = 1 to 24). This stops error accumulation.</p>
									</div>
								</div>
								<div class="rule-card">
									<div class="rule-icon"><CheckCircle2 size={15} class="text-emerald" /></div>
									<div class="rule-content">
										<strong>Sub-50 Millisecond Laptop Execution</strong>
										<p>Inference completes in under 25 milliseconds on standard laptop CPUs, enabling high-frequency supervisory dispatch.</p>
									</div>
								</div>

							{:else if activeStage === 'guard'}
								<div class="rule-card">
									<div class="rule-icon"><SlidersHorizontal size={15} class="text-emerald" /></div>
									<div class="rule-content">
										<strong>Hard Nocturnal Solar Zeroing</strong>
										<p>When forecasted solar irradiance is 0.0 W/m² (sun is down), solar power output is strictly forced to 0.0 kW, eliminating statistical noise.</p>
									</div>
								</div>
								<div class="rule-card">
									<div class="rule-icon"><SlidersHorizontal size={15} class="text-emerald" /></div>
									<div class="rule-content">
										<strong>Inverter Hardware Ceiling (50.0 kW)</strong>
										<p>Solar generation cannot physically exceed the electrical rating of the inverter. Power is clipped at 50.0 kW.</p>
									</div>
								</div>
								<div class="rule-card">
									<div class="rule-icon"><CheckCircle2 size={15} class="text-emerald" /></div>
									<div class="rule-content">
										<strong>Facility Load Bounding</strong>
										<p>Building power demand is kept strictly between the 10.0 kW baseload and 45.0 kW peak capacity.</p>
									</div>
								</div>

							{:else if activeStage === 'dispatch'}
								<div class="rule-card">
									<div class="rule-icon"><BatteryCharging size={15} class="text-emerald" /></div>
									<div class="rule-content">
										<strong>Calculate Instantaneous Power Balance</strong>
										<p><strong>Net Power</strong> = Solar Power minus Building Load Demand.</p>
									</div>
								</div>
								<div class="rule-card">
									<div class="rule-icon"><CheckCircle2 size={15} class="text-emerald" /></div>
									<div class="rule-content">
										<strong>Solar Surplus: Charge Battery</strong>
										<p>When solar generation exceeds building demand (Net &gt; 0), excess electricity routes into battery storage for later use.</p>
									</div>
								</div>
								<div class="rule-card">
									<div class="rule-icon"><AlertTriangle size={15} class="text-rose" /></div>
									<div class="rule-content">
										<strong>Power Deficit: Discharge Battery</strong>
										<p>When building demand exceeds solar generation (Net &lt; 0), stored battery energy discharges to avoid high peak-hour grid electricity tariffs.</p>
									</div>
								</div>
							{/if}
						</div>
					{:else}
						<!-- Technical Spec Mode -->
						<div class="tech-spec-container font-mono">
							{#if activeStage === 'sanitizer'}
								<div class="spec-block">
									<span class="spec-label">MODULE:</span>
									<code>ml_service/features/sanitizer.py :: TelemetrySanitizer</code>
								</div>
								<div class="spec-block">
									<span class="spec-label">INPUT SCHEMA:</span>
									<code>['timestamp', 'ghi', 'temp_amb', 'cloud_cover', 'p_pv', 'p_load']</code>
								</div>
								<div class="spec-block">
									<span class="spec-label">FREQUENCY & GAP LIMIT:</span>
									<p>Enforces <code>freq='h'</code> DatetimeIndex. Gaps &le; 3h linearly interpolated; Gaps &gt; 3h raise <code>TelemetryGapError</code>.</p>
								</div>
							{:else if activeStage === 'conditioning'}
								<div class="spec-block">
									<span class="spec-label">MODULE:</span>
									<code>ml_service/features/pipeline.py :: FeaturePipeline</code>
								</div>
								<div class="spec-block">
									<span class="spec-label">FROZEN LAG FEATURES:</span>
									<code>p_pv_lag_0, p_pv_lag_1, p_pv_lag_23, p_pv_lag_24</code>
								</div>
								<div class="spec-block">
									<span class="spec-label">ROLLING SUMMARY VECTORS:</span>
									<code>mean_6h, std_6h, mean_24h, std_24h (computed strictly on [T-48h..T])</code>
								</div>
								<div class="spec-block">
									<span class="spec-label">HORIZON CONDITIONING:</span>
									<p>Conditioned on relative integer <code>h &in; [1..24]</code>, sin/cos hour, and sin/cos day-of-year.</p>
								</div>
							{:else if activeStage === 'inference'}
								<div class="spec-block">
									<span class="spec-label">ESTIMATOR:</span>
									<code>lightgbm.LGBMRegressor(n_estimators=150, max_depth=6, num_leaves=31)</code>
								</div>
								<div class="spec-block">
									<span class="spec-label">TRAINING MATRIX:</span>
									<p>~8,688 origin steps expanded into 208,512 rows across 1 continuous year. CPU training time: ~2.5s per model.</p>
								</div>
								<div class="spec-block">
									<span class="spec-label">VALIDATION ACCURACY:</span>
									<p>PV Daylight nMAE: 0.26% (SLA &le; 5.0%) • Load 24h nMAE: 2.99% (SLA &le; 6.0%) • R&sup2; &gt; 0.93.</p>
								</div>
							{:else if activeStage === 'guard'}
								<div class="spec-block">
									<span class="spec-label">POST-PROCESSING:</span>
									<code>ml_service/postprocessing/boundary_enforcer.py</code>
								</div>
								<div class="spec-block">
									<span class="spec-label">PHYSICAL EQUATIONS:</span>
									<code>P̂_pv = clip(P̂_pv, 0.0, 50.0) &times; 1_{'{GHI > 0}'}</code><br/>
									<code>P̂_load = clip(P̂_load, 10.0, 45.0 &times; 1.2)</code>
								</div>
							{:else if activeStage === 'dispatch'}
								<div class="spec-block">
									<span class="spec-label">DISPATCH FORMULATION:</span>
									<code>P_net = P̂_pv - P̂_load</code>
								</div>
								<div class="spec-block">
									<span class="spec-label">OPTIMIZER TARGET:</span>
									<p>Downstream Mixed-Integer Linear Program (MILP) battery state-of-charge (SoC) arbitrage against time-of-use tariffs.</p>
								</div>
							{/if}
						</div>
					{/if}
				</div>

				<!-- Right Column: Visual Architecture / Context Graphic -->
				<div class="inspector-col visual-col">
					<h4 class="col-heading font-mono">
						<span>SYSTEM VISUALIZATION & DATA CONTEXT</span>
					</h4>

					{#if activeStage === 'sanitizer'}
						<div class="context-card font-mono">
							<span class="card-title-mini">SELF-HEALING THRESHOLDS</span>
							<div class="threshold-diagram">
								<div class="thresh-item good">
									<span class="thresh-val">0 to 3 Hours</span>
									<span class="thresh-status">✓ Auto-Healed</span>
									<span class="thresh-desc">Sensor packet loss. Linear interpolation recovers contiguous stream.</span>
								</div>
								<div class="thresh-divider"></div>
								<div class="thresh-item bad">
									<span class="thresh-val">&gt; 3 Hours</span>
									<span class="thresh-status">⚠ Supervisory Alarm</span>
									<span class="thresh-desc">Extended hardware outage. Stops pipeline to avoid hallucinated inputs.</span>
								</div>
							</div>
						</div>

					{:else if activeStage === 'conditioning'}
						<!-- Spacious Visual Lag Timeline Map -->
						<div class="context-card font-mono">
							<div class="lag-map-title-row">
								<span class="card-title-mini">WHY PAST MEASUREMENTS (LAGS) MATTER (ADR 0001)</span>
								<span class="badge-mini font-mono">Origin Locked</span>
							</div>

							<p class="lag-intuitive-text font-sans">
								Electrical demand repeats in daily 24-hour cycles. What the building used yesterday at 2:00 PM is the strongest baseline for predicting today at 2:00 PM.
							</p>

							<div class="spacious-lag-timeline">
								<div class="timeline-lane past-lane">
									<span class="lane-title">PAST READINGS (LOCKED AT TIME T)</span>
									<div class="lane-chips">
										<div class="chip-item">
											<span class="chip-k">T - 24h</span>
											<span class="chip-v">Daily baseline match</span>
										</div>
										<div class="chip-item">
											<span class="chip-k">T - 6h..T</span>
											<span class="chip-v">Rolling 6h moving mean</span>
										</div>
										<div class="chip-item">
											<span class="chip-k">T - 1h</span>
											<span class="chip-v">Immediate momentum ramp</span>
										</div>
										<div class="chip-item anchor-item">
											<span class="chip-k">Time T</span>
											<span class="chip-v">🔒 Anchor origin</span>
										</div>
									</div>
								</div>

								<div class="lock-barrier-row">
									<div class="lock-line"></div>
									<div class="lock-badge-pill">
										<Lock size={12} class="text-sky" />
										<span>ZERO LEAKAGE BARRIER</span>
									</div>
									<div class="lock-line"></div>
								</div>

								<div class="timeline-lane future-lane">
									<span class="lane-title">24-HOUR FORWARD HORIZON</span>
									<div class="future-steps-row">
										<div class="step-chip">T+1h</div>
										<div class="step-chip">T+2h</div>
										<div class="step-chip">T+3h</div>
										<div class="step-chip">...</div>
										<div class="step-chip">T+24h</div>
									</div>
									<span class="future-weather-hint">+ 24h Numerical Weather Forecasts (GHI, Temp, Cloud)</span>
								</div>
							</div>
						</div>

					{:else if activeStage === 'inference'}
						<div class="context-card font-mono">
							<span class="card-title-mini">DUAL PARALLEL ESTIMATOR FLOW</span>
							<div class="dual-model-diagram">
								<div class="model-lane pv-lane">
									<div class="model-box">
										<span class="model-name">Solar LightGBM</span>
										<span class="model-stat">50.0 kW Capacity</span>
									</div>
									<span class="model-out">Solar Forecast (P̂_pv)</span>
								</div>
								<div class="model-lane load-lane">
									<div class="model-box">
										<span class="model-name">Load LightGBM</span>
										<span class="model-stat">45.0 kW Peak</span>
									</div>
									<span class="model-out">Building Demand (P̂_load)</span>
								</div>
							</div>
							<div class="inference-speed-badge">
								<span>Evaluates all 24 horizons simultaneously in <strong>{latencyMs.toFixed(1)} ms</strong></span>
							</div>
						</div>

					{:else if activeStage === 'guard'}
						<div class="context-card font-mono">
							<span class="card-title-mini">PHYSICAL HARDWARE BOUNDARIES</span>
							<div class="bounds-stack">
								<div class="bound-row">
									<span class="bound-name">Solar Night Bound:</span>
									<span class="bound-rule">GHI &le; 0 &rarr; 0.0 kW strictly enforced</span>
								</div>
								<div class="bound-row">
									<span class="bound-name">Inverter Ceiling:</span>
									<span class="bound-rule">P̂_pv capped at 50.0 kW</span>
								</div>
								<div class="bound-row">
									<span class="bound-name">Building Baseload:</span>
									<span class="bound-rule">P̂_load baseline &ge; 10.0 kW</span>
								</div>
							</div>
						</div>

					{:else if activeStage === 'dispatch'}
						<div class="context-card font-mono">
							<span class="card-title-mini">24-HOUR ENERGY SUMMARY</span>
							<div class="dispatch-summary-box">
								<div class="summary-line">
									<span>Total Solar Generation:</span>
									<strong class="text-amber">{totalPvKwh.toFixed(1)} kWh</strong>
								</div>
								<div class="summary-line">
									<span>Total Facility Demand:</span>
									<strong class="text-sky">{totalLoadKwh.toFixed(1)} kWh</strong>
								</div>
								<div class="summary-line">
									<span>Solar Load Coverage:</span>
									<strong>{solarCoveragePct}%</strong>
								</div>
								<div class="summary-line highlight-line">
									<span>Net Storage Balance:</span>
									<strong class={netBalanceKwh >= 0 ? 'text-emerald' : 'text-rose'}>
										{netBalanceKwh >= 0 ? '+' : ''}{netBalanceKwh.toFixed(1)} kWh
									</strong>
								</div>
							</div>
						</div>
					{/if}
				</div>
			</div>
		</section>
	{/if}
</div>

<style>
	.pipeline-panel {
		background: var(--surface);
		border-radius: var(--radius-core);
		box-shadow: var(--bezel);
		overflow: hidden;
		display: flex;
		flex-direction: column;
		width: 100%;
	}

	.pipeline-header {
		display: flex;
		justify-content: space-between;
		align-items: flex-end;
		padding: 1.75rem 2rem 1.4rem;
		border-bottom: 1px solid var(--hairline);
		flex-wrap: wrap;
		gap: 1rem 1.5rem;
	}

	.pipeline-title {
		margin: 0;
		font-family: var(--font-display);
		font-size: 1.85rem;
		font-weight: 400;
		line-height: 1.1;
		letter-spacing: -0.015em;
		color: var(--text-primary);
	}

	.pipeline-subtitle {
		margin: 0.45rem 0 0;
		font-size: 0.85rem;
		color: var(--text-muted);
	}

	.pipeline-meta {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		font-size: 0.74rem;
	}

	.mode-toggle-btn {
		background: var(--surface-sunken);
		border: 1px solid var(--hairline-strong);
		color: var(--text-secondary);
		padding: 0.35rem 0.75rem;
		border-radius: 999px;
		font-size: 0.72rem;
		cursor: pointer;
		transition: all 0.25s var(--ease);
	}

	.mode-toggle-btn:hover {
		color: var(--text-primary);
		background: var(--surface-soft);
	}

	.mode-toggle-btn.active {
		background: rgba(2, 132, 199, 0.15);
		color: var(--color-load-ink);
		border-color: rgba(2, 132, 199, 0.4);
	}

	.source-tag {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.35rem 0.8rem;
		border-radius: 999px;
		background: var(--surface-sunken);
		color: var(--text-secondary);
	}

	.source-tag::before {
		content: '';
		width: 6px;
		height: 6px;
		border-radius: 50%;
		background: var(--color-pv);
	}

	.source-tag.live::before {
		background: var(--color-surplus);
	}

	.latency-tag {
		color: var(--text-muted);
	}

	/* Dataflow ribbon */
	.dataflow-ribbon {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0.75rem 2rem;
		background: rgba(18, 16, 14, 0.5);
		border-bottom: 1px solid var(--hairline);
		overflow-x: auto;
		gap: 0.75rem;
	}

	.flow-node {
		display: inline-flex;
		align-items: center;
		gap: 0.45rem;
		background: transparent;
		border: 1px solid transparent;
		color: var(--text-muted);
		font-size: 0.72rem;
		padding: 0.3rem 0.65rem;
		border-radius: 999px;
		cursor: pointer;
		white-space: nowrap;
		transition: all 0.25s var(--ease);
	}

	.flow-node:hover {
		color: var(--text-primary);
		background: var(--surface-sunken);
	}

	.flow-node.active {
		color: var(--text-primary);
		background: var(--surface-sunken);
		border-color: var(--hairline-strong);
		font-weight: 500;
	}

	:global(.flow-arrow) {
		color: var(--hairline-strong);
		user-select: none;
		flex-shrink: 0;
	}

	/* Balanced 5 Stage Cards Grid */
	.stages-overview-grid {
		display: grid;
		grid-template-columns: repeat(5, minmax(0, 1fr));
		width: 100%;
		border-bottom: 1px solid var(--hairline);
	}

	@media (max-width: 992px) {
		.stages-overview-grid {
			grid-template-columns: 1fr;
		}

		.stage-card {
			border-right: none !important;
			border-bottom: 1px solid var(--hairline);
		}

		.stage-card:last-child {
			border-bottom: none;
		}
	}

	.stage-card {
		padding: 1.4rem 1.25rem 1.2rem;
		border: none;
		border-right: 1px solid var(--hairline);
		background: transparent;
		text-align: left;
		display: flex;
		flex-direction: column;
		justify-content: space-between;
		gap: 1rem;
		cursor: pointer;
		transition: all 0.3s var(--ease);
		position: relative;
	}

	.stage-card:hover {
		background: rgba(255, 255, 255, 0.02);
	}

	.stage-card.selected {
		background: rgba(255, 255, 255, 0.035);
		box-shadow: inset 0 2px 0 var(--color-pv);
	}

	.stage-card:last-child {
		border-right: none;
	}

	.card-head {
		display: flex;
		align-items: flex-start;
		gap: 0.65rem;
	}

	.stage-num-badge {
		width: 24px;
		height: 24px;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		border-radius: 50%;
		background: var(--surface-sunken);
		border: 1px solid var(--hairline-strong);
		font-size: 0.62rem;
		color: var(--text-secondary);
		flex-shrink: 0;
	}

	.stage-card.selected .stage-num-badge {
		background: var(--color-pv-muted);
		color: var(--color-pv-ink);
		border-color: var(--color-pv);
	}

	.stage-label-group {
		min-width: 0;
	}

	.stage-card-title {
		margin: 0;
		font-size: 0.88rem;
		font-weight: 600;
		color: var(--text-primary);
		line-height: 1.25;
	}

	.stage-card-sub {
		display: block;
		font-size: 0.7rem;
		color: var(--text-muted);
		margin-top: 0.15rem;
		line-height: 1.3;
	}

	.card-stats {
		display: flex;
		flex-direction: column;
		gap: 0.35rem;
		font-size: 0.72rem;
		border-top: 1px solid var(--hairline);
		padding-top: 0.65rem;
	}

	.card-stat-row {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 0.5rem;
	}

	.stat-lbl {
		color: var(--text-muted);
	}

	.stat-num {
		color: var(--text-primary);
		font-weight: 500;
	}

	.stat-num.highlight {
		color: var(--color-pv-ink);
	}

	.stat-num.surplus {
		color: var(--color-surplus-ink);
	}

	.stat-num.deficit {
		color: var(--color-deficit-ink);
	}

	.stat-badge {
		font-size: 0.64rem;
		padding: 0.1rem 0.5rem;
		border-radius: 999px;
		background: var(--surface-sunken);
		color: var(--text-secondary);
	}

	.stat-badge.healed {
		background: var(--color-pv-muted);
		color: var(--color-pv-ink);
	}

	.stat-badge.anchor-badge {
		background: rgba(2, 132, 199, 0.15);
		color: var(--color-load-ink);
	}

	.mini-energy-bar {
		height: 4px;
		width: 100%;
		border-radius: 999px;
		overflow: hidden;
		display: flex;
		background: var(--surface-sunken);
		margin-bottom: 0.2rem;
	}

	.energy-chunk {
		height: 100%;
	}

	.pv-chunk {
		background: var(--color-pv);
	}

	.load-chunk {
		background: var(--color-load);
	}

	.card-footer {
		display: flex;
		justify-content: flex-end;
	}

	.action-hint {
		font-size: 0.65rem;
		color: var(--text-muted);
		transition: color 0.25s ease;
	}

	.stage-card:hover .action-hint,
	.stage-card.selected .action-hint {
		color: var(--text-primary);
	}

	/* Wide, Full-Width Detail Inspector Panel */
	.wide-inspector-panel {
		background: var(--surface-soft);
		border-bottom: 1px solid var(--hairline);
		padding: 1.75rem 2rem 2rem;
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
		animation: reveal 0.4s var(--ease) both;
	}

	@keyframes reveal {
		from {
			opacity: 0;
			transform: translateY(8px);
		}
		to {
			opacity: 1;
			transform: none;
		}
	}

	.inspector-header {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		gap: 1.5rem;
		border-bottom: 1px solid var(--hairline);
		padding-bottom: 1.25rem;
	}

	.inspector-title-group {
		display: flex;
		align-items: flex-start;
		gap: 1rem;
	}

	.inspector-icon-pill {
		width: 38px;
		height: 38px;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		border-radius: 12px;
		background: var(--surface-sunken);
		border: 1px solid var(--hairline-strong);
		flex-shrink: 0;
	}

	.inspector-badge-row {
		display: flex;
		align-items: center;
		gap: 0.65rem;
		margin-bottom: 0.25rem;
	}

	.stage-tag {
		font-size: 0.62rem;
		font-weight: 700;
		letter-spacing: 0.08em;
		color: var(--color-pv-ink);
	}

	.spec-mode-badge {
		font-size: 0.62rem;
		color: var(--text-muted);
		background: var(--surface-sunken);
		padding: 0.15rem 0.5rem;
		border-radius: 999px;
	}

	.inspector-title {
		margin: 0;
		font-size: 1.25rem;
		font-weight: 600;
		color: var(--text-primary);
		letter-spacing: -0.01em;
	}

	.close-inspector-btn {
		display: inline-flex;
		align-items: center;
		gap: 0.4rem;
		background: var(--surface-sunken);
		border: 1px solid var(--hairline-strong);
		color: var(--text-secondary);
		padding: 0.35rem 0.85rem;
		border-radius: 999px;
		font-size: 0.72rem;
		cursor: pointer;
		transition: all 0.25s var(--ease);
	}

	.close-inspector-btn:hover {
		color: var(--text-primary);
		background: var(--surface);
	}

	/* Spacious 2-Column Inspector Layout */
	.inspector-body-grid {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 2rem;
		align-items: start;
	}

	@media (max-width: 900px) {
		.inspector-body-grid {
			grid-template-columns: 1fr;
			gap: 1.5rem;
		}
	}

	.inspector-col {
		display: flex;
		flex-direction: column;
		gap: 0.9rem;
	}

	.col-heading {
		margin: 0;
		font-size: 0.68rem;
		font-weight: 700;
		letter-spacing: 0.08em;
		color: var(--text-muted);
	}

	.rules-list {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.rule-card {
		display: flex;
		gap: 0.85rem;
		align-items: flex-start;
		background: var(--surface-sunken);
		border: 1px solid var(--hairline);
		border-radius: var(--radius-inner);
		padding: 0.95rem 1.1rem;
	}

	.rule-icon {
		flex-shrink: 0;
		margin-top: 0.1rem;
	}

	.rule-content {
		display: flex;
		flex-direction: column;
		gap: 0.2rem;
		font-size: 0.8rem;
	}

	.rule-content strong {
		color: var(--text-primary);
	}

	.rule-content p {
		margin: 0;
		color: var(--text-secondary);
		line-height: 1.45;
	}

	/* Tech Spec Mode Container */
	.tech-spec-container {
		display: flex;
		flex-direction: column;
		gap: 0.85rem;
		background: var(--surface-sunken);
		border: 1px solid var(--hairline);
		border-radius: var(--radius-inner);
		padding: 1.25rem;
		font-size: 0.74rem;
	}

	.spec-block {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
	}

	.spec-label {
		font-size: 0.64rem;
		font-weight: 700;
		color: var(--color-pv-ink);
		letter-spacing: 0.06em;
	}

	.spec-block code {
		color: var(--text-primary);
		background: rgba(255, 255, 255, 0.04);
		padding: 0.25rem 0.5rem;
		border-radius: 4px;
		display: inline-block;
	}

	.spec-block p {
		margin: 0;
		color: var(--text-secondary);
		line-height: 1.45;
	}

	/* Right Visual Context Cards */
	.context-card {
		background: var(--surface-sunken);
		border: 1px solid var(--hairline);
		border-radius: var(--radius-inner);
		padding: 1.25rem;
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.card-title-mini {
		font-size: 0.68rem;
		font-weight: 700;
		letter-spacing: 0.08em;
		color: var(--color-load-ink);
	}

	.lag-map-title-row {
		display: flex;
		justify-content: space-between;
		align-items: center;
	}

	.badge-mini {
		font-size: 0.62rem;
		background: rgba(2, 132, 199, 0.15);
		color: var(--color-load-ink);
		padding: 0.15rem 0.5rem;
		border-radius: 999px;
	}

	.lag-intuitive-text {
		margin: 0;
		font-size: 0.8rem;
		color: var(--text-secondary);
		line-height: 1.5;
	}

	.spacious-lag-timeline {
		display: flex;
		flex-direction: column;
		gap: 0.85rem;
	}

	.timeline-lane {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.lane-title {
		font-size: 0.62rem;
		color: var(--text-muted);
		letter-spacing: 0.05em;
	}

	.lane-chips {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 0.5rem;
	}

	.chip-item {
		background: rgba(255, 255, 255, 0.03);
		border: 1px solid var(--hairline-strong);
		padding: 0.45rem 0.65rem;
		border-radius: 6px;
		display: flex;
		flex-direction: column;
		gap: 0.1rem;
	}

	.chip-item.anchor-item {
		border-color: rgba(2, 132, 199, 0.4);
		background: rgba(2, 132, 199, 0.1);
	}

	.chip-k {
		font-size: 0.74rem;
		font-weight: 700;
		color: var(--text-primary);
	}

	.chip-v {
		font-size: 0.65rem;
		color: var(--text-muted);
	}

	.lock-barrier-row {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		margin: 0.2rem 0;
	}

	.lock-line {
		flex: 1;
		height: 1px;
		background: dashed 1px var(--hairline-strong);
	}

	.lock-badge-pill {
		display: inline-flex;
		align-items: center;
		gap: 0.4rem;
		font-size: 0.64rem;
		font-weight: 700;
		color: #eab308;
		background: rgba(234, 179, 8, 0.1);
		border: 1px solid rgba(234, 179, 8, 0.3);
		padding: 0.25rem 0.65rem;
		border-radius: 999px;
		letter-spacing: 0.05em;
	}

	.future-steps-row {
		display: flex;
		gap: 0.4rem;
		flex-wrap: wrap;
	}

	.step-chip {
		background: rgba(255, 255, 255, 0.03);
		border: 1px solid var(--hairline);
		padding: 0.25rem 0.55rem;
		border-radius: 4px;
		font-size: 0.7rem;
		color: var(--text-secondary);
	}

	.future-weather-hint {
		font-size: 0.65rem;
		color: var(--text-muted);
	}

	/* Threshold diagram for Stage 01 */
	.threshold-diagram {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.thresh-item {
		display: flex;
		flex-direction: column;
		gap: 0.2rem;
		padding: 0.75rem;
		border-radius: 6px;
		font-size: 0.72rem;
	}

	.thresh-item.good {
		background: rgba(18, 160, 113, 0.06);
		border: 1px solid rgba(18, 160, 113, 0.25);
	}

	.thresh-item.bad {
		background: rgba(224, 54, 95, 0.06);
		border: 1px solid rgba(224, 54, 95, 0.25);
	}

	.thresh-val {
		font-weight: 700;
		font-size: 0.8rem;
		color: var(--text-primary);
	}

	.thresh-status {
		font-weight: 600;
		font-size: 0.72rem;
	}

	.thresh-item.good .thresh-status { color: var(--color-surplus-ink); }
	.thresh-item.bad .thresh-status { color: var(--color-deficit-ink); }

	.thresh-desc {
		font-size: 0.68rem;
		color: var(--text-secondary);
	}

	/* Stage 03 Dual Model Diagram */
	.dual-model-diagram {
		display: flex;
		gap: 1rem;
	}

	.model-lane {
		flex: 1;
		display: flex;
		flex-direction: column;
		gap: 0.4rem;
	}

	.model-box {
		background: rgba(255, 255, 255, 0.04);
		border: 1px solid var(--hairline-strong);
		padding: 0.75rem;
		border-radius: 6px;
		display: flex;
		flex-direction: column;
		gap: 0.2rem;
	}

	.model-name {
		font-weight: 600;
		color: var(--text-primary);
		font-size: 0.76rem;
	}

	.model-stat {
		font-size: 0.68rem;
		color: var(--text-muted);
	}

	.model-out {
		font-size: 0.66rem;
		color: var(--color-pv-ink);
	}

	.load-lane .model-out {
		color: var(--color-load-ink);
	}

	.inference-speed-badge {
		font-size: 0.7rem;
		color: var(--text-secondary);
		background: var(--surface-soft);
		padding: 0.5rem 0.75rem;
		border-radius: 4px;
	}

	/* Stage 04 Bounds stack */
	.bounds-stack {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		font-size: 0.74rem;
	}

	.bound-row {
		display: flex;
		justify-content: space-between;
		padding: 0.45rem 0;
		border-bottom: 1px solid var(--hairline);
	}

	.bound-name {
		color: var(--text-muted);
	}

	.bound-rule {
		color: var(--text-primary);
		font-weight: 500;
	}

	/* Stage 05 Dispatch summary */
	.dispatch-summary-box {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		font-size: 0.75rem;
	}

	.summary-line {
		display: flex;
		justify-content: space-between;
		color: var(--text-secondary);
	}

	.summary-line.highlight-line {
		border-top: 1px solid var(--hairline);
		padding-top: 0.5rem;
		font-size: 0.8rem;
	}

	/* Text colors */
	.text-amber { color: var(--color-pv-ink); }
	.text-sky { color: var(--color-load-ink); }
	.text-emerald { color: var(--color-surplus-ink); }
	.text-rose { color: var(--color-deficit-ink); }

	@media (max-width: 760px) {
		.pipeline-header {
			padding-inline: 1.25rem;
		}

		.wide-inspector-panel {
			padding-inline: 1.25rem;
		}

		.lane-chips {
			grid-template-columns: 1fr;
		}
	}
</style>

<script lang="ts">
	interface Props {
		isOpen: boolean;
		onClose: () => void;
	}

	let { isOpen = false, onClose }: Props = $props();

	type TabId = 'workflow' | 'inputs' | 'outputs' | 'glossary';
	let activeTab = $state<TabId>('workflow');

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape' && isOpen) {
			onClose();
		}
	}
</script>

<svelte:window onkeydown={handleKeydown} />

{#if isOpen}
	<div class="modal-backdrop" onclick={onClose} role="presentation">
		<!-- svelte-ignore a11y_click_events_have_key_events -->
		<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
		<div
			class="modal-window"
			role="dialog"
			aria-modal="true"
			tabindex="-1"
			aria-labelledby="modal-title"
			onclick={(e) => e.stopPropagation()}
		>
			<!-- Header -->
			<div class="modal-header">
				<div>
					<h2 id="modal-title" class="modal-title">System architecture & specifications</h2>
					<p class="modal-subtitle">Autonomous 24-hour microgrid forecasting and dispatch methodology</p>
				</div>
				<button class="close-btn" onclick={onClose} aria-label="Close guide">
					✕
				</button>
			</div>

			<!-- Tabs (Segmented, no misaligned borders) -->
			<div class="modal-tabs">
				<button
					class="tab-btn font-mono"
					class:active={activeTab === 'workflow'}
					onclick={() => (activeTab = 'workflow')}
				>Pipeline workflow</button>
				<button
					class="tab-btn font-mono"
					class:active={activeTab === 'inputs'}
					onclick={() => (activeTab = 'inputs')}
				>Required feeds</button>
				<button
					class="tab-btn font-mono"
					class:active={activeTab === 'outputs'}
					onclick={() => (activeTab = 'outputs')}
				>Forecast envelopes</button>
				<button
					class="tab-btn font-mono"
					class:active={activeTab === 'glossary'}
					onclick={() => (activeTab = 'glossary')}
				>Parameters & units</button>
			</div>

			<!-- Body -->
			<div class="modal-body">
				{#if activeTab === 'workflow'}
					<div class="tab-pane">
						<div class="callout-box">
							<h3>Architecture principle (ADR 0001)</h3>
							<p>Origin-anchored horizon conditioning evaluates all 24 future hours simultaneously in under 25 milliseconds on standard CPU. This directly prevents autoregressive drift and compounding multi-step error accumulation.</p>
						</div>

						<div class="workflow-steps">
							<div class="workflow-step">
								<span class="step-num font-mono">01</span>
								<div class="step-text">
									<h4>Self-healing telemetry sanitizer</h4>
									<p>Ingests the 48-hour historical lookback buffer. Telemetry dropouts up to 3 hours caused by packet loss are automatically healed via linear interpolation and nocturnal zero-filling.</p>
								</div>
							</div>

							<div class="workflow-step">
								<span class="step-num font-mono">02</span>
								<div class="step-text">
									<h4>Frozen origin anchor & forward weather</h4>
									<p>Observed history is frozen strictly at origin moment T to guarantee zero future data leakage. Combines upcoming 24-hour numerical weather predictions with calendar encodings.</p>
								</div>
							</div>

							<div class="workflow-step">
								<span class="step-num font-mono">03</span>
								<div class="step-text">
									<h4>Parallel LightGBM regressor inference</h4>
									<p>Two specialized gradient-boosted decision tree models infer simultaneously: one for solar PV generation and one for facility electrical demand.</p>
								</div>
							</div>

							<div class="workflow-step">
								<span class="step-num font-mono">04</span>
								<div class="step-text">
									<h4>Deterministic physical guardrails</h4>
									<p>Physics enforcement guarantees hard 0.0 kW nocturnal solar output when GHI ≤ 0, enforces inverter clipping at 50.0 kW, and binds load demand to [10..45 kW].</p>
								</div>
							</div>

							<div class="workflow-step">
								<span class="step-num font-mono">05</span>
								<div class="step-text">
									<h4>Battery storage economic arbitrage</h4>
									<p>Calculates instantaneous net power (Solar − Load). Solar surplus charges the battery storage; load deficit triggers optimal battery discharge to minimize peak grid tariffs.</p>
								</div>
							</div>
						</div>
					</div>

				{:else if activeTab === 'inputs'}
					<div class="tab-pane">
						<div class="split-columns">
							<div class="col-panel">
								<h3>Operator controls</h3>
								<div class="feed-list">
									<div class="feed-item">
										<strong>Forecast origin (T)</strong>
										<p>The temporal anchor moment. Historical context spans [T-48h..T]; predictions project [T+1h..T+24h].</p>
									</div>
									<div class="feed-item">
										<strong>Scenario presets</strong>
										<p>Seasonal weather archetypes (Summer peak, Winter evening, Spring ramp, Storm front) to stress-test microgrid dynamics.</p>
									</div>
									<div class="feed-item">
										<strong>Dropout simulator</strong>
										<p>Injects synthetic sensor communication blackouts to test automated pipeline self-healing in real time.</p>
									</div>
								</div>
							</div>

							<div class="col-panel">
								<h3>Automated telemetry & weather</h3>
								<div class="feed-list">
									<div class="feed-item">
										<strong>48-Hour sensor buffer</strong>
										<p>Continuous rolling logs of panel output (kW), building demand (kW), outdoor temperature (°C), and irradiance (W/m²).</p>
									</div>
									<div class="feed-item">
										<strong>24-Hour NWP weather forecast</strong>
										<p>Upcoming numerical predictions of solar irradiance (GHI), ambient temperature (°C), and cloud cover (%).</p>
									</div>
									<div class="feed-item">
										<strong>Cyclical calendar encodings</strong>
										<p>Hour of day, day of week, and day of year to account for facility shifts and occupancy patterns.</p>
									</div>
								</div>
							</div>
						</div>
					</div>

				{:else if activeTab === 'outputs'}
					<div class="tab-pane">
						<div class="output-stack">
							<div class="output-card">
								<span class="output-type font-mono">Stream 01</span>
								<h3>Solar PV generation (P̂_pv)</h3>
								<p>Predicted photovoltaic electrical output for each hour of the 24-hour horizon.</p>
								<div class="output-meta font-mono">
									<span>Unit: Kilowatts (kW)</span>
									<span>Rating: 50.0 kW inverter ceiling</span>
									<span>Physics: Strictly 0.0 kW nocturnal zeroing</span>
								</div>
							</div>

							<div class="output-card">
								<span class="output-type font-mono">Stream 02</span>
								<h3>Facility load demand (P̂_load)</h3>
								<p>Predicted building electrical power consumption across equipment, lighting, and HVAC systems.</p>
								<div class="output-meta font-mono">
									<span>Unit: Kilowatts (kW)</span>
									<span>Capacity: 10.0 kW baseload to 45.0 kW peak</span>
									<span>Rhythm: Workday morning ramp and evening domestic draw</span>
								</div>
							</div>

							<div class="output-card">
								<span class="output-type font-mono">Derived schedule</span>
								<h3>Net power & battery schedule</h3>
								<p>Real-time power balance: P̂_net = P̂_pv − P̂_load.</p>
								<div class="output-meta font-mono">
									<span>Surplus: Charges on-site battery storage</span>
									<span>Deficit: Discharges battery or imports grid power</span>
									<span>Energy: 24h integrated sum (kWh) for economic dispatch</span>
								</div>
							</div>
						</div>
					</div>

				{:else if activeTab === 'glossary'}
					<div class="tab-pane">
						<div class="table-container font-mono">
							<table class="glossary-table">
								<thead>
									<tr>
										<th>Term</th>
										<th>Unit</th>
										<th>Category</th>
										<th>Operational definition</th>
									</tr>
								</thead>
								<tbody>
									<tr>
										<td><strong>kW (Kilowatt)</strong></td>
										<td>Power</td>
										<td>Metric</td>
										<td>Instantaneous rate of electricity generated or consumed.</td>
									</tr>
									<tr>
										<td><strong>kWh (Kilowatt-hour)</strong></td>
										<td>Energy</td>
										<td>Metric</td>
										<td>Total volume of electrical energy over time (1 kW for 1h = 1 kWh).</td>
									</tr>
									<tr>
										<td><strong>Solar PV (P_pv)</strong></td>
										<td>kW</td>
										<td>Asset</td>
										<td>Photovoltaic electrical output. Inverter ceiling: 50.0 kW.</td>
									</tr>
									<tr>
										<td><strong>Load demand (P_load)</strong></td>
										<td>kW</td>
										<td>Asset</td>
										<td>Facility electrical consumption. Baseload: 10.0 kW; Peak: 45.0 kW.</td>
									</tr>
									<tr>
										<td><strong>GHI irradiance</strong></td>
										<td>W/m²</td>
										<td>Weather</td>
										<td>Global Horizontal Irradiance: solar intensity per square meter.</td>
									</tr>
									<tr>
										<td><strong>Ambient temperature</strong></td>
										<td>°C</td>
										<td>Weather</td>
										<td>Outdoor air temperature influencing cooling and panel efficiency.</td>
									</tr>
									<tr>
										<td><strong>nMAE accuracy</strong></td>
										<td>%</td>
										<td>SLA Quality</td>
										<td>Normalized Mean Absolute Error relative to capacity. PV: 0.26%, Load: 2.99%.</td>
									</tr>
								</tbody>
							</table>
						</div>
					</div>
				{/if}
			</div>

			<!-- Footer -->
			<div class="modal-footer">
				<button class="return-btn" onclick={onClose}>
					Close guide
				</button>
			</div>
		</div>
	</div>
{/if}

<style>
	@keyframes fade-in {
		from {
			opacity: 0;
		}
		to {
			opacity: 1;
		}
	}

	@keyframes pop-in {
		from {
			opacity: 0;
			transform: translateY(14px) scale(0.98);
		}
		to {
			opacity: 1;
			transform: none;
		}
	}

	.modal-backdrop {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.72);
		backdrop-filter: blur(14px);
		-webkit-backdrop-filter: blur(14px);
		z-index: 1000;
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 1.5rem;
		animation: fade-in 0.4s var(--ease) both;
	}

	.modal-window {
		background: var(--surface);
		border-radius: 28px;
		width: 100%;
		max-width: 860px;
		max-height: 85dvh;
		display: flex;
		flex-direction: column;
		box-shadow:
			0 0 0 1px var(--hairline-strong),
			0 40px 80px -20px rgba(0, 0, 0, 0.9);
		overflow: hidden;
		animation: pop-in 0.6s var(--ease) both;
	}

	.modal-header {
		padding: 1.75rem 2rem 1.25rem;
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		gap: 1rem;
	}

	.modal-title {
		margin: 0;
		font-family: var(--font-display);
		font-size: 1.9rem;
		font-weight: 400;
		line-height: 1.1;
		letter-spacing: -0.015em;
		color: var(--text-primary);
	}

	.modal-subtitle {
		margin: 0.45rem 0 0;
		font-size: 0.85rem;
		color: var(--text-muted);
	}

	.close-btn {
		flex-shrink: 0;
		width: 34px;
		height: 34px;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		background: var(--surface-sunken);
		color: var(--text-secondary);
		border-radius: 50%;
		font-size: 0.8rem;
		transition:
			background-color 0.4s var(--ease),
			color 0.4s var(--ease),
			transform 0.5s var(--ease);
	}

	.close-btn:hover {
		background: var(--surface-hover);
		color: var(--text-primary);
	}

	.close-btn:active {
		transform: scale(0.94);
	}

	/* Segmented tab track */
	.modal-tabs {
		display: flex;
		align-items: center;
		gap: 2px;
		width: fit-content;
		max-width: calc(100% - 4rem);
		margin: 0 2rem;
		padding: 3px;
		background: var(--surface-sunken);
		border-radius: 999px;
		overflow-x: auto;
		scrollbar-width: none;
	}

	.modal-tabs::-webkit-scrollbar {
		display: none;
	}

	.tab-btn {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		height: 34px;
		padding: 0 1rem;
		background: transparent;
		color: var(--text-secondary);
		font-family: var(--font-sans);
		font-size: 0.78rem;
		font-weight: 500;
		line-height: 1;
		white-space: nowrap;
		border-radius: 999px;
		transition:
			background-color 0.4s var(--ease),
			color 0.4s var(--ease),
			box-shadow 0.4s var(--ease);
	}

	.tab-btn:hover {
		color: var(--text-primary);
	}

	.tab-btn.active {
		background: var(--surface);
		color: var(--text-primary);
		box-shadow:
			0 0 0 1px var(--hairline),
			0 2px 6px -2px rgba(23, 21, 15, 0.16);
	}

	.modal-body {
		padding: 1.5rem 2rem 1.75rem;
		overflow-y: auto;
		flex: 1;
	}

	.tab-pane {
		display: flex;
		flex-direction: column;
		gap: 1.25rem;
	}

	.callout-box {
		background: var(--color-pv-muted);
		border-radius: 18px;
		padding: 1.25rem 1.5rem;
	}

	.callout-box h3 {
		margin: 0 0 0.4rem;
		font-size: 0.92rem;
		font-weight: 600;
		color: var(--text-primary);
	}

	.callout-box p {
		margin: 0;
		font-size: 0.82rem;
		color: var(--text-secondary);
		line-height: 1.6;
	}

	.workflow-steps,
	.output-stack {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.workflow-step,
	.col-panel,
	.output-card {
		background: var(--surface-soft);
		box-shadow: inset 0 0 0 1px var(--hairline);
		border-radius: 18px;
	}

	.workflow-step {
		display: flex;
		gap: 1rem;
		align-items: flex-start;
		padding: 1.1rem 1.35rem;
	}

	.step-num {
		flex-shrink: 0;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 28px;
		height: 28px;
		border-radius: 50%;
		background: var(--surface);
		box-shadow: inset 0 0 0 1px var(--hairline-strong);
		font-size: 0.66rem;
		font-weight: 500;
		color: var(--text-secondary);
	}

	.step-text h4 {
		margin: 0.2rem 0 0.3rem;
		font-size: 0.9rem;
		font-weight: 600;
		letter-spacing: -0.01em;
		color: var(--text-primary);
	}

	.step-text p {
		margin: 0;
		font-size: 0.8rem;
		color: var(--text-secondary);
		line-height: 1.55;
	}

	.split-columns {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
		gap: 1.25rem;
	}

	.col-panel {
		padding: 1.4rem 1.5rem;
		display: flex;
		flex-direction: column;
		gap: 1.1rem;
	}

	.col-panel h3 {
		margin: 0;
		font-size: 0.95rem;
		font-weight: 600;
		letter-spacing: -0.01em;
		color: var(--text-primary);
	}

	.feed-list {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.feed-item strong {
		font-size: 0.82rem;
		font-weight: 600;
		color: var(--text-primary);
		display: block;
		margin-bottom: 0.2rem;
	}

	.feed-item p {
		margin: 0;
		font-size: 0.78rem;
		color: var(--text-secondary);
		line-height: 1.55;
	}

	.output-card {
		padding: 1.35rem 1.5rem;
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.output-type {
		font-family: var(--font-sans);
		font-size: 0.66rem;
		font-weight: 500;
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: var(--text-muted);
	}

	.output-card h3 {
		margin: 0;
		font-size: 0.95rem;
		font-weight: 600;
		letter-spacing: -0.01em;
		color: var(--text-primary);
	}

	.output-card p {
		margin: 0;
		font-size: 0.82rem;
		color: var(--text-secondary);
		line-height: 1.55;
	}

	.output-meta {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem 1.25rem;
		margin-top: 0.35rem;
		font-size: 0.72rem;
		color: var(--text-muted);
	}

	.table-container {
		border-radius: var(--radius-inner);
		box-shadow: inset 0 0 0 1px var(--hairline);
		overflow-y: auto;
		max-height: 360px;
	}

	.glossary-table {
		width: 100%;
		border-collapse: collapse;
		font-family: var(--font-sans);
		font-size: 0.8rem;
		text-align: left;
	}

	.glossary-table th {
		background: var(--surface-soft);
		color: var(--text-muted);
		padding: 0.8rem 1rem;
		font-size: 0.66rem;
		font-weight: 500;
		letter-spacing: 0.1em;
		text-transform: uppercase;
		border-bottom: 1px solid var(--hairline);
		position: sticky;
		top: 0;
	}

	.glossary-table td {
		padding: 0.8rem 1rem;
		border-bottom: 1px solid var(--hairline);
		color: var(--text-secondary);
		line-height: 1.5;
		vertical-align: top;
	}

	.glossary-table td strong {
		color: var(--text-primary);
		font-weight: 600;
	}

	.glossary-table tr:last-child td {
		border-bottom: none;
	}

	.modal-footer {
		padding: 1rem 2rem 1.5rem;
		display: flex;
		justify-content: flex-end;
		border-top: 1px solid var(--hairline);
	}

	.return-btn {
		background: var(--cta-bg);
		color: var(--cta-fg);
		border-radius: 999px;
		padding: 0.65rem 1.5rem;
		font-size: 0.82rem;
		font-weight: 600;
		transition:
			background-color 0.4s var(--ease),
			transform 0.5s var(--ease);
	}

	.return-btn:hover {
		background: var(--cta-hover);
	}

	.return-btn:active {
		transform: scale(0.98);
	}

	@media (max-width: 760px) {
		.modal-backdrop {
			padding: 0.75rem;
		}

		.modal-header,
		.modal-body,
		.modal-footer {
			padding-inline: 1.25rem;
		}

		.modal-tabs {
			margin-inline: 1.25rem;
			max-width: calc(100% - 2.5rem);
		}

		.modal-title {
			font-size: 1.55rem;
		}
	}
</style>

<script lang="ts">
	import favicon from '$lib/assets/favicon.svg';

	let { children } = $props();
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<title>Helios — 24H Microgrid Forecast & Dispatch</title>
</svelte:head>

<div class="app-viewport">
	<div class="app-container">
		{@render children()}
	</div>
</div>

<style>
	:global(:root) {
		/* Deep pitch-black substrate with sleek functional accents */
		--bg-base: #000000;
		--bg-surface: #09090C;
		--bg-surface-elevated: #121217;
		--bg-surface-subtle: #050507;
		--bg-hover: #181820;

		/* Razor-sharp borders */
		--border-subtle: #1C1C24;
		--border-medium: #2C2C38;
		--border-strong: #444454;

		/* Clean functional accents (restrained, zero neon glow) */
		--color-pv: #F59E0B;            /* Crisp Solar Amber */
		--color-pv-muted: rgba(245, 158, 11, 0.12);
		
		--color-load: #38BDF8;          /* Ice Blue */
		--color-load-muted: rgba(56, 189, 248, 0.12);

		--color-surplus: #10B981;       /* Emerald Green (Net +ve) */
		--color-surplus-muted: rgba(16, 185, 129, 0.14);
		--color-deficit: #F43F5E;       /* Rose Red (Net -ve) */
		--color-deficit-muted: rgba(244, 63, 94, 0.14);
		--color-warn: #F59E0B;

		/* High-contrast typography */
		--text-primary: #FFFFFF;
		--text-secondary: #A1A1AA;
		--text-muted: #71717A;
		--text-faint: #3F3F46;

		--font-sans: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
		--font-mono: 'JetBrains Mono', ui-monospace, SFMono-Regular, monospace;

		--ease-out: cubic-bezier(0.16, 1, 0.3, 1);
	}

	:global(*) {
		box-sizing: border-box;
	}

	:global(body) {
		margin: 0;
		padding: 0;
		background-color: var(--bg-base);
		color: var(--text-primary);
		font-family: var(--font-sans);
		-webkit-font-smoothing: antialiased;
		-moz-osx-font-smoothing: grayscale;
		min-height: 100vh;
		overflow-x: hidden;
	}

	:global(button) {
		font-family: inherit;
		cursor: pointer;
		user-select: none;
		border: none;
		outline: none;
		background: none;
		box-sizing: border-box;
		line-height: inherit;
	}

	.app-viewport {
		min-height: 100vh;
		width: 100%;
		display: flex;
		flex-direction: column;
		background-color: var(--bg-base);
	}

	.app-container {
		width: 100%;
		min-height: 100vh;
		display: flex;
		flex-direction: column;
	}

	/* Minimal scrollbar */
	:global(::-webkit-scrollbar) {
		width: 5px;
		height: 5px;
	}

	:global(::-webkit-scrollbar-track) {
		background: #000000;
	}

	:global(::-webkit-scrollbar-thumb) {
		background: #27272A;
		border-radius: 2px;
	}

	:global(::-webkit-scrollbar-thumb:hover) {
		background: #3F3F46;
	}
</style>

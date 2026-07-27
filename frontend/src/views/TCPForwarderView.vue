<template>
  <div class="tcp-forwarder-page">
    <section class="tcp-forwarder-hero">
      <div class="tcp-forwarder-hero__heading">
        <span class="tcp-forwarder-hero__icon">
          <n-icon><GitNetworkOutline /></n-icon>
        </span>
        <div>
          <p class="eyebrow">{{ $t('auto.5253082b80bd') }}</p>
          <h2>{{ $t('auto.0a9bdeadb13c') }}</h2>
          <p> {{ $t('auto.bc05fab48151') }} </p>
        </div>
      </div>
      <n-button type="primary" round size="large" :disabled="!canDownload" @click="downloadScript">
        <template #icon><n-icon><DownloadOutline /></n-icon></template> {{ $t('auto.83ca4197bc9b') }} </n-button>

      <div class="tcp-forwarder-flow" :aria-label="$t('auto.68d8996616d4')">
        <article class="tcp-forwarder-node tcp-forwarder-node--product">
          <span class="tcp-forwarder-node__icon"><n-icon><DesktopOutline /></n-icon></span>
          <span class="tcp-forwarder-node__step">{{ $t('auto.cbe4dfa4b988') }}</span>
          <strong>Oxo Tracker</strong>
          <small>{{ $t('auto.aa864f6abe26') }}</small>
          <code>{{ externalEndpoint }}</code>
        </article>

        <div class="tcp-forwarder-link">
          <span>{{ $t('auto.b65463cb6a42') }}</span>
          <n-icon><ArrowForwardOutline /></n-icon>
          <small>{{ $t('auto.6b5c6a4b8ac0') }}</small>
        </div>

        <article class="tcp-forwarder-node tcp-forwarder-node--relay">
          <span class="tcp-forwarder-node__badge">{{ $t('auto.8879efe809e8') }}</span>
          <span class="tcp-forwarder-node__icon"><n-icon><SwapHorizontalOutline /></n-icon></span>
          <span class="tcp-forwarder-node__step">{{ $t('auto.ab4ee2be65bc') }}</span>
          <strong>{{ $t('auto.b350d71631fa') }}</strong>
          <small>{{ $t('auto.480775d63ec5') }}</small>
          <code>{{ listenAddress }}</code>
        </article>

        <div class="tcp-forwarder-link">
          <span>{{ $t('auto.ba4e72261283') }}</span>
          <n-icon><ArrowForwardOutline /></n-icon>
          <small>{{ $t('auto.f3a9c6cc8f54') }}</small>
        </div>

        <article class="tcp-forwarder-node tcp-forwarder-node--target">
          <span class="tcp-forwarder-node__icon"><n-icon><ServerOutline /></n-icon></span>
          <span class="tcp-forwarder-node__step">{{ $t('auto.e2489d80709b') }}</span>
          <strong>{{ $t('auto.b7c8b6b966a1') }}</strong>
          <small>{{ $t('auto.bc35db0daa1b') }}</small>
          <code>{{ targetAddress }}</code>
        </article>
      </div>
    </section>

    <div class="tcp-forwarder-workspace">
      <section class="tcp-forwarder-panel tcp-forwarder-form-panel">
        <div class="tcp-forwarder-panel__head">
          <span class="tcp-forwarder-panel__number">01</span>
          <div>
            <p class="eyebrow">{{ $t('auto.ab30a5cd5d8b') }}</p>
            <h3>{{ $t('auto.5784021fcfea') }}</h3>
            <span>{{ $t('auto.3bc544d51f99') }}</span>
          </div>
        </div>

        <div class="tcp-forwarder-form-section">
          <div class="tcp-forwarder-form-section__title">
            <span><n-icon><RadioOutline /></n-icon></span>
            <div>
              <strong>{{ $t('auto.7939468b83b0') }}</strong>
              <small>{{ $t('auto.920620734791') }}</small>
            </div>
          </div>
          <div class="tcp-forwarder-fields">
            <label>
              <span>{{ $t('auto.da0500646662') }}</span>
              <n-input v-model:value="form.listenHost" placeholder="0.0.0.0" />
              <small>{{ $t('auto.51b4b8748fb0') }}</small>
            </label>
            <label>
              <span>{{ $t('auto.b8451c1b51f2') }}</span>
              <n-input-number v-model:value="form.listenPort" :min="1" :max="65535" />
              <small>{{ $t('auto.e0e26f8a6e65') }}</small>
            </label>
          </div>
        </div>

        <div class="tcp-forwarder-form-section">
          <div class="tcp-forwarder-form-section__title">
            <span><n-icon><CloudOutline /></n-icon></span>
            <div>
              <strong>{{ $t('auto.cce5473e7935') }}</strong>
              <small>{{ $t('auto.bc64ff783888') }}</small>
            </div>
          </div>
          <div class="tcp-forwarder-fields">
            <label>
              <span>{{ $t('auto.5e52ec500744') }}</span>
              <n-input v-model:value="form.targetHost" placeholder="192.168.50.21" />
              <small>{{ $t('auto.2388c5654b9a') }}</small>
            </label>
            <label>
              <span>{{ $t('auto.86bba8c9a54b') }}</span>
              <n-input-number v-model:value="form.targetPort" :min="1" :max="65535" />
              <small>{{ $t('auto.b4bd11dba98b') }}</small>
            </label>
          </div>
        </div>

        <div v-if="validationMessage" class="tcp-forwarder-validation">
          <n-icon><InformationCircleOutline /></n-icon>
          <span>{{ validationMessage }}</span>
        </div>
      </section>

      <section class="tcp-forwarder-panel tcp-forwarder-preview-panel">
        <div class="tcp-forwarder-panel__head">
          <span class="tcp-forwarder-panel__number">02</span>
          <div>
            <p class="eyebrow">{{ $t('auto.1e9cde85965e') }}</p>
            <h3>{{ $t('auto.ad4f45d01e1e') }}</h3>
            <span>{{ $t('auto.28dfeaf915b4') }}</span>
          </div>
        </div>

        <div class="tcp-forwarder-route-preview">
          <span>
            <small>{{ $t('auto.c518fb067439') }}</small>
            <strong>{{ listenAddress }}</strong>
          </span>
          <n-icon><ArrowForwardOutline /></n-icon>
          <span>
            <small>{{ $t('auto.44c59f80f347') }}</small>
            <strong>{{ targetAddress }}</strong>
          </span>
        </div>

        <div class="tcp-forwarder-script-preview">
          <div>
            <span><n-icon><TerminalOutline /></n-icon> {{ $t('auto.6814f21f9054') }}</span>
            <code>{{ fileName }}</code>
          </div>
          <pre>{{ scriptPreview }}</pre>
        </div>

        <div class="tcp-forwarder-requirements">
          <span><n-icon><ShieldCheckmarkOutline /></n-icon></span>
          <div>
            <strong>{{ $t('auto.e6a818b9c342') }}</strong>
            <small>{{ $t('auto.a00e700a2510') }}</small>
          </div>
        </div>

        <code class="tcp-forwarder-run-command">python3 {{ fileName }}</code>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive } from 'vue'
import { useMessage } from 'naive-ui'
import {
  ArrowForwardOutline,
  CloudOutline,
  DesktopOutline,
  DownloadOutline,
  GitNetworkOutline,
  InformationCircleOutline,
  RadioOutline,
  ServerOutline,
  ShieldCheckmarkOutline,
  SwapHorizontalOutline,
  TerminalOutline,
} from '@vicons/ionicons5'

interface ForwarderForm {
  listenHost: string
  listenPort: number | null
  targetHost: string
  targetPort: number | null
}

const message = useMessage()
const form = reactive<ForwarderForm>({
  listenHost: '0.0.0.0',
  listenPort: 9000,
  targetHost: '192.168.50.21',
  targetPort: 8002,
})

const validHostPattern = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,252}$/

function validPort(value: number | null) {
  return Number.isInteger(value) && Number(value) >= 1 && Number(value) <= 65535
}

function validHost(value: string) {
  return validHostPattern.test(value.trim())
}

const validationMessage = computed(() => {
  if (!validHost(form.listenHost)) return 'Enter a valid listening IP address or hostname without spaces.'
  if (!validPort(form.listenPort)) return 'Listen port must be between 1 and 65535.'
  if (!validHost(form.targetHost)) return 'Enter a valid target IP address or hostname without spaces.'
  if (!validPort(form.targetPort)) return 'Target port must be between 1 and 65535.'
  return ''
})

const canDownload = computed(() => !validationMessage.value)
const listenAddress = computed(() => `${form.listenHost.trim() || '0.0.0.0'}:${form.listenPort || '—'}`)
const targetAddress = computed(() => `${form.targetHost.trim() || '<TARGET_HOST>'}:${form.targetPort || '—'}`)
const publicRelayHost = computed(() => form.listenHost.trim() === '0.0.0.0' ? '<RELAY_IP>' : form.listenHost.trim())
const externalEndpoint = computed(() => `http://${publicRelayHost.value}:${form.listenPort || '—'}`)
const fileName = computed(() => `oxo-tcp-forwarder-${form.listenPort || 'port'}.py`)

const generatedScript = computed(() => `#!/usr/bin/env python3
import asyncio
import subprocess

LISTEN_HOST = ${JSON.stringify(form.listenHost.trim())}
LISTEN_PORT = ${Number(form.listenPort || 0)}

TARGET_HOST = ${JSON.stringify(form.targetHost.trim())}
TARGET_PORT = ${Number(form.targetPort || 0)}

GREEN = "\\033[92m"
CYAN = "\\033[96m"
YELLOW = "\\033[93m"
RED = "\\033[91m"
RESET = "\\033[0m"


def get_relay_ip():
    """Return the first non-loopback IPv4 address."""
    try:
        return subprocess.check_output(
            ["hostname", "-I"],
            text=True,
        ).split()[0]
    except (IndexError, subprocess.SubprocessError):
        return "<RELAY_IP>"


async def relay(reader, writer):
    try:
        while data := await reader.read(65536):
            writer.write(data)
            await writer.drain()
    except (ConnectionError, asyncio.CancelledError):
        pass


async def handle_client(client_reader, client_writer):
    peer = client_writer.get_extra_info("peername")
    print(f"{GREEN}[+] Client connected: {peer}{RESET}")

    try:
        target_reader, target_writer = await asyncio.open_connection(
            TARGET_HOST,
            TARGET_PORT,
        )
    except Exception as exc:
        print(f"{RED}[-] Unable to connect to target: {exc}{RESET}")
        client_writer.close()
        await client_writer.wait_closed()
        return

    tasks = [
        asyncio.create_task(relay(client_reader, target_writer)),
        asyncio.create_task(relay(target_reader, client_writer)),
    ]

    try:
        _, pending = await asyncio.wait(
            tasks,
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
    finally:
        target_writer.close()
        client_writer.close()
        await asyncio.gather(
            target_writer.wait_closed(),
            client_writer.wait_closed(),
            return_exceptions=True,
        )
        print(f"{YELLOW}[-] Client disconnected: {peer}{RESET}")


async def main():
    server = await asyncio.start_server(
        handle_client,
        LISTEN_HOST,
        LISTEN_PORT,
    )
    relay_ip = get_relay_ip()

    print(f"""
{CYAN}╔══════════════════════════════════════════╗
║     Oxo Tracker TCP Port Forwarder       ║
╚══════════════════════════════════════════╝{RESET}

{YELLOW}Port mapping:{RESET}
  {LISTEN_HOST}:{LISTEN_PORT}
         ↓
  {TARGET_HOST}:{TARGET_PORT}

{GREEN}External access:{RESET}
  {GREEN}http://{relay_ip}:{LISTEN_PORT}{RESET}

{GREEN}Chat endpoint:{RESET}
  {GREEN}http://{relay_ip}:{LISTEN_PORT}/chat{RESET}

Press Ctrl+C to stop the forwarder.
""")

    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\\n{YELLOW}[*] Forwarder stopped{RESET}")
`)

const scriptPreview = computed(() => `#!/usr/bin/env python3
import asyncio
import subprocess

LISTEN_HOST = ${JSON.stringify(form.listenHost.trim())}
LISTEN_PORT = ${Number(form.listenPort || 0)}

TARGET_HOST = ${JSON.stringify(form.targetHost.trim())}
TARGET_PORT = ${Number(form.targetPort || 0)}

# … relay implementation included in download`)

function downloadScript() {
  if (!canDownload.value) {
    message.error(validationMessage.value)
    return
  }
  const blob = new Blob([generatedScript.value], { type: 'text/x-python;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = fileName.value
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.setTimeout(() => URL.revokeObjectURL(url), 30_000)
  message.success(`${fileName.value} downloaded. Run it on the relay computer.`)
}
</script>

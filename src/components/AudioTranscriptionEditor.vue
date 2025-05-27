<template>
  <div class="app-container">
    <div class="sticky-header">
      <h2 class="title">Fichiers Audio & Transcriptions</h2>

      <div v-if="successMessage" class="toast">{{ successMessage }}</div>

      <!-- Navigation rapide -->
      <div class="navigation-controls" v-if="visibleFiles.length">
        <button @click="goToPrevious" :disabled="!hasPrevious" class="nav-btn">←</button>
        <span class="nav-status">Segment {{ currentIndexDisplay + 1 }} / {{ audioFiles.length }}</span>
        <button @click="goToNext" :disabled="!hasNext" class="nav-btn">→</button>
      </div>
    </div>

    <div v-for="file in visibleFiles" :key="file.id" class="row">
      <div class="file-info">
        <p class="filename">{{ file.name }}</p>
        <div class="feedback-buttons">
          <button aria-disabled="false" type="button" class="feedback-button" aria-label="Like" data-state="closed">
            <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-thumbs-up">
              <path d="M7 10v12"></path>
              <path d="M15 5.88 14 10h5.83a2 2 0 0 1 1.92 2.56l-2.33 8A2 2 0 0 1 17.5 22H4a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2h2.76a2 2 0 0 0 1.79-1.11L12 2a3.13 3.13 0 0 1 3 3.88Z"></path>
            </svg>
          </button>
          <button aria-disabled="false" type="button" class="feedback-button" aria-label="Dislike" data-state="closed">
            <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-thumbs-down">
              <path d="M17 14V2"></path>
              <path d="M9 18.12 10 14H4.17a2 2 0 0 1-1.92-2.56l2.33-8A2 2 0 0 1 6.5 2H20a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-2.76a2 2 0 0 0-1.79 1.11L12 22a3.13 3.13 0 0 1-3-3.88Z"></path>
            </svg>
          </button>
        </div>
      </div>

      <audio
        :ref="el => audioRefs[file.id] = el"
        :src="file.url"
        controls
        class="audio-player"
        @play="currentFocusedId = file.id"
      ></audio>
      
      <div class="column transcription-col">
        <!-- Système de notation par étoiles -->
        <div class="star-rating">
          <span
            v-for="n in 5"
            :key="n"
            class="star"
            :class="{ filled: n <= file.rating }"
            @click="onRatingSelected(file, n)"
          >
            ★
          </span>
        </div>

        <textarea
          v-model="file.transcription"
          :class="{ empty: file.transcription === '' }"
          :ref="el => textareas[file.id] = el"
          @focus="currentFocusedId = file.id"
          placeholder="Veuillez entrer la transcription ici..."
        ></textarea>
        <button @click="validate(file.id)" class="edit-btn">Valider</button>

        <details v-if="file.history && file.history.length > 1" class="history-log">
          <summary class="history-title">🕒 Historique des modifications</summary>
          <ul>
            <li v-for="(entry, idx) in file.history.slice(0, -1).reverse()" :key="idx" class="history-entry">
              <span class="timestamp">🗓️ {{ new Date(entry.timestamp).toLocaleString() }}</span><br />
              <span class="content text-sm italic">{{ entry.transcription }}</span>
            </li>
          </ul>
        </details>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, computed, nextTick } from 'vue'

const audioFiles = ref([])
const visibleFiles = ref([])
const successMessage = ref('')
const BATCH_SIZE = 5
let currentIndex = 0

const textareas = {}
const audioRefs = {}
const currentFocusedId = ref(null)

const currentIndexDisplay = computed(() => {
  const id = currentFocusedId.value
  const idx = audioFiles.value.findIndex(f => f.id === id)
  return idx >= 0 ? idx : 0
})

const hasPrevious = computed(() => currentIndexDisplay.value > 0)
const hasNext = computed(() => currentIndexDisplay.value < audioFiles.value.length - 1)

function goToPrevious() {
  const prev = audioFiles.value[currentIndexDisplay.value - 1]
  if (prev) focusTextarea(prev.id)
}

function goToNext() {
  const next = audioFiles.value[currentIndexDisplay.value + 1]
  if (next) focusTextarea(next.id)
}

function focusTextarea(id) {
  nextTick(() => {
    const el = textareas[id]
    if (el) el.focus()
    currentFocusedId.value = id
  })
}

function loadMore() {
  const nextBatch = audioFiles.value.slice(currentIndex, currentIndex + BATCH_SIZE)
  visibleFiles.value.push(...nextBatch)
  currentIndex += BATCH_SIZE
}

function handleScroll() {
  if (window.innerHeight + window.scrollY >= document.body.offsetHeight - 100) {
    loadMore()
  }
}

async function validate(id) {
  const file = visibleFiles.value.find(f => f.id === id)
  try {
    const res = await fetch('/api/save-transcription', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: file.name, transcription: file.transcription })
    })
    if (!res.ok) throw new Error('Erreur lors de la sauvegarde.')
    if (!file.history) file.history = []
    file.history.push({ transcription: file.transcription, timestamp: new Date().toISOString() })
    successMessage.value = `✅ Transcription « ${file.name} » validée !`
    setTimeout(() => (successMessage.value = ''), 3000)
  } catch (err) {
    console.error(err)
    successMessage.value = `❌ Erreur : ${err.message}`
    setTimeout(() => (successMessage.value = ''), 4000)
  }
}

async function onRatingSelected(file, rating) {
  file.rating = rating
  try {
    const res = await fetch(`/api/save-rating/${file.id}`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ rating })
    })
    if (!res.ok) throw new Error('Erreur enregistrement note')
    successMessage.value = `⭐ Note de ${rating} enregistrée !`
    setTimeout(() => (successMessage.value = ''), 2000)
  } catch (err) {
    console.error(err)
    successMessage.value = `❌ ${err.message}`
    setTimeout(() => (successMessage.value = ''), 3000)
  }
}

function handleKeydown(e) {
  if (e.code === 'Space' && document.activeElement.tagName !== 'TEXTAREA') {
    e.preventDefault()
    const audio = audioRefs[currentFocusedId.value]
    if (audio) {
      audio.paused ? audio.play() : audio.pause()
    }
  }
  if (e.ctrlKey && e.key === 'Enter') {
    e.preventDefault()
    validate(currentFocusedId.value)
  }
}

onMounted(async () => {
  const res = await fetch('/api/audio-files')
  audioFiles.value = await res.json()
  loadMore()
  window.addEventListener('scroll', handleScroll, { passive: true })
  window.addEventListener('keydown', handleKeydown)
})

onBeforeUnmount(() => {
  window.removeEventListener('scroll', handleScroll)
  window.removeEventListener('keydown', handleKeydown)
})
</script>

<style scoped>
.navigation-controls {
  display: flex; justify-content: center; align-items: center; gap: 1rem; margin-bottom: 1rem;
}
.nav-btn {
  background-color: var(--success-color); border: none; padding: 0.5rem 1rem; color: white; cursor: pointer; border-radius: 4px; font-weight: 500;
}
.nav-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.nav-status { color: var(--text-color); font-weight: 500; }
.audio-player { width: 100%; margin-top: 0.5rem; }
.row { display: flex; gap: 1rem; margin-bottom: 2rem; }
.audio-col { flex: 1; }
.transcription-col { flex: 2; display: flex; flex-direction: column; gap: 0.5rem; }
.transcription-col textarea { width: 100%; min-height: 100px; padding: 0.5rem; border: 1px solid #ccc; border-radius: 4px; }
.edit-btn { align-self: start; background: var(--btn-bg-color); color: white; border: none; padding: 0.5rem 1rem; border-radius: 4px; cursor: pointer; }
.history-log { margin-top: 0.5rem; }
.star-rating { display: flex; align-items: center; margin-bottom: 0.5rem; }
.star { font-size: 24px; cursor: pointer; color: #ccc; margin-right: 4px; }
.star.filled { color: gold; }
.toast { background: #4caf50; color: white; padding: 0.5rem 1rem; border-radius: 4px; animation: fade-in-out 2s ease-in-out; position: sticky; top: 4rem; }
@keyframes fade-in-out { 0%,100% { opacity: 0; } 10%,90% { opacity: 1; } }
</style>

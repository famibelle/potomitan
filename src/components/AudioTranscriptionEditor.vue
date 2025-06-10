<template>
  <div class="app-container">
    <div class="sticky-header">
      <h2 class="title">Maké an Kréyol Gwadloup</h2>

      <div v-if="successMessage" class="toast">{{ successMessage }}</div>

      <!-- Navigation rapide -->
      <div class="navigation-controls" v-if="visibleFiles.length">
        <span class="nav-status">Segment {{ currentIndexDisplay + 1 }} / {{ audioFiles.length }}</span>
        <div class="nav-btn-group">
          <button @click="shuffleFiles" class="nav-btn" title="Mélanger l'ordre des fichiers">🔀</button>
          <button @click="sortByLikes" class="nav-btn" title="Trier par nombre de likes">👍🏿</button>
          <button @click="sortByDislikes" class="nav-btn" title="Trier par nombre de dislikes">👎🏿</button>
          <button @click="sortByStars" class="nav-btn" title="Trier par nombre d'étoiles (cliquer à nouveau pour inverser)">★</button>
          <button class="nav-btn" title="Notifications" @click="toggleNotifications"> 🔔 <span class="notification-badge">{{ notificationCount }}</span> </button>
        </div>
      </div>
    </div>

    <div v-for="file in visibleFiles" :key="file.id" class="row">
      <div class="file-info">
        <p class="filename">{{ file.name }}</p>
        <div class="feedback-buttons">
          <button aria-disabled="false" type="button" class="feedback-button" aria-label="Like" data-state="closed" @click="onLike(file)" title="J'aime ce segment !">
            👍🏿
            <span class="feedback-count">{{ file.likes ?? 0 }}</span>
          </button>
          |
          <button aria-disabled="false" type="button" class="feedback-button" aria-label="Dislike" data-state="closed" @click="onDislike(file)" title="Je n'aime pas ce segment">
            👎🏿
            <span class="feedback-count">{{ file.dislikes ?? 0 }}</span>
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
          <span class="rating-label">Notez la transcription: </span>
          <span
            v-for="n in 5"
            :key="n"
            class="star"
            :class="{ filled: n <= file.rating }"
            @click="onRatingSelected(file, n)"
            :title="`Donner ${n} étoile${n > 1 ? 's' : ''}`"
          >
            {{ n <= file.rating ? '★' : '☆' }}
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

    <!-- Notifications -->
    <div v-if="showNotifications" class="notifications-panel">
      <h3 class="notifications-title">Notifications</h3>
      <button class="close-btn" @click="toggleNotifications">✖️</button>
      <button class="mark-read-btn" @click="updatePreviousState" style="margin-bottom:1rem;">Marquer comme lu</button>
      <div v-if="notifications.length === 0" class="no-notifications">
        Aucune nouvelle notification.
      </div>
      <div v-for="(notif, idx) in notifications.slice()" :key="idx" class="notification-item">
        <template v-if="notif.type === 'like'">
          👍🏿 Nouveau like sur <b>{{ notif.fileName }}</b>
          <span v-if="notif.timestamp" class="notif-time">— {{ new Date(notif.timestamp).toLocaleString() }}</span>
        </template>
        <template v-else-if="notif.type === 'dislike'">
          👎🏿 Nouveau dislike sur <b>{{ notif.fileName }}</b>
          <span v-if="notif.timestamp" class="notif-time">— {{ new Date(notif.timestamp).toLocaleString() }}</span>
        </template>
        <template v-else-if="notif.type === 'transcription'">
          📝 Nouvelle transcription sur <b>{{ notif.fileName }}</b>
          <span v-if="notif.timestamp" class="notif-time">— {{ new Date(notif.timestamp).toLocaleString() }}</span>
          <div class="notif-content">"{{ notif.content }}"</div>
        </template>
        <template v-else-if="notif.type === 'rating'">
          ⭐ Note modifiée sur <b>{{ notif.fileName }}</b> : {{ notif.newRating }}
          <span v-if="notif.timestamp" class="notif-time">— {{ new Date(notif.timestamp).toLocaleString() }}</span>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, computed, nextTick, watch } from 'vue'

const audioFiles = ref([])
const visibleFiles = ref([])
const successMessage = ref('')
const BATCH_SIZE = 5
let currentIndex = 0

const textareas = {}
const audioRefs = {}
const currentFocusedId = ref(null)
const showNotifications = ref(false);

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

function shuffleFiles() {
  // Mélanger les fichiers
  audioFiles.value.sort(() => Math.random() - 0.5)
  // Réinitialiser les fichiers visibles
  visibleFiles.value = []
  currentIndex = 0
  loadMore()
}

function sortByLikes() {
  audioFiles.value.sort((a, b) => (b.likes ?? 0) - (a.likes ?? 0));
  visibleFiles.value = [];
  currentIndex = 0;
  loadMore();
}

function sortByDislikes() {
  audioFiles.value.sort((a, b) => (b.dislikes ?? 0) - (a.dislikes ?? 0));
  visibleFiles.value = [];
  currentIndex = 0;
  loadMore();
}

const sortState = ref({ field: null, asc: true });

function sortByStars() {
  if (sortState.value.field === 'rating') {
    sortState.value.asc = !sortState.value.asc;
  } else {
    sortState.value.field = 'rating';
    sortState.value.asc = false;
  }
  audioFiles.value.sort((a, b) => {
    const diff = (b.rating ?? 0) - (a.rating ?? 0);
    return sortState.value.asc ? -diff : diff;
  });
  visibleFiles.value = [];
  currentIndex = 0;
  loadMore();
}

async function validate(id) {
  const file = visibleFiles.value.find(f => f.id === id)
  try {
    const res = await fetch('/api/save-transcription', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: file.name, transcription: file.transcription })
    })
    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      if (res.status === 409 && data.error && data.error.includes('déjà été proposée')) {
        throw new Error('Cette transcription a déjà été proposée')
      }
      throw new Error(data.error || 'Erreur lors de la sauvegarde.')
    }
    if (!file.history) file.history = []
    file.history.push({ transcription: file.transcription, timestamp: new Date().toISOString() })
    successMessage.value = `✅ Transcription « ${file.name} » validée !`
    setTimeout(() => (successMessage.value = ''), 3000)
    await addNotification('transcription', file, { content: file.transcription });
  } catch (err) {
    console.error(err)
    successMessage.value = `❌ ${err.message}`
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
    await addNotification('rating', file, { newRating: rating });
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

async function onLike(file) {
  file.likes = (file.likes ?? 0) + 1
  try {
    const res = await fetch('/api/like', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ fileId: file.id })
    })
    if (!res.ok) throw new Error('Erreur lors du like')
    await addNotification('like', file)
  } catch (err) {
    file.likes = (file.likes ?? 1) - 1
  }
}

async function onDislike(file) {
  file.dislikes = (file.dislikes ?? 0) + 1
  try {
    const res = await fetch('/api/dislike', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ fileId: file.id })
    })
    if (!res.ok) throw new Error('Erreur lors du dislike')
    await addNotification('dislike', file)
  } catch (err) {
    file.dislikes = (file.dislikes ?? 1) - 1
  }
}

// Charger la liste brute des notifications depuis le serveur
const notifications = ref([]);

async function loadNotifications() {
  try {
    const res = await fetch('/api/notifications-state');
    if (res.ok) {
      notifications.value = await res.json();
    } else {
      notifications.value = [];
    }
  } catch (e) {
    notifications.value = [];
  }
}

async function addNotification(type, file, extra = {}) {
  // Crée une notification simple
  const notif = {
    type,
    fileId: file.id,
    fileName: file.name,
    timestamp: new Date().toISOString(),
    ...extra
  };
  // Ajoute côté client
  notifications.value.push(notif);
  // Sauvegarde côté serveur (envoie uniquement la dernière notif)
  await fetch('/api/notifications-state', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify([notif])
  });
}

async function clearNotifications() {
  notifications.value = [];
  await fetch('/api/notifications-state', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify([])
  });
}

// Remplacer updatePreviousState par clearNotifications
function updatePreviousState() {
  clearNotifications();
}

// Le compteur de notifications devient simplement la longueur du tableau
const notificationCount = computed(() => notifications.value.length);

// Charger les notifications au démarrage
onMounted(async () => {
  await loadNotifications();
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

function toggleNotifications() {
  showNotifications.value = !showNotifications.value;
  if (showNotifications.value) {
    loadNotifications(); // recharge la liste à chaque ouverture du panneau
  }
}
</script>

<style scoped>
.navigation-controls {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.5rem;
  margin-bottom: 1rem;
}
.nav-btn-group {
  display: flex;
  gap: 1rem;
}
.nav-btn {
  background-color: var(--success-color); border: none; padding: 0.5rem 1rem; color: white; cursor: pointer; border-radius: 4px; font-weight: 500;
}
.nav-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.nav-status { color: var(--text-color); font-weight: 500; white-space: nowrap; }
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
.history-entry {
  text-align: left;
}
.filename, .rating-label {
  font-size: 1.1rem;
  font-weight: 500;
}
.notifications-panel {
  position: fixed;
  top: 0;
  right: 0;
  width: 300px;
  max-width: 80%;
  height: 100%;
  background: white;
  box-shadow: -2px 0 5px rgba(0, 0, 0, 0.2);
  padding: 1rem;
  z-index: 1000;
  overflow-y: auto;
  animation: slide-in 0.3s ease-out;
  text-align: left; /* Ajouté pour aligner le texte à gauche */
}
.notifications-title {
  font-size: 1.2rem;
  font-weight: 600;
  margin-bottom: 1rem;
}
.close-btn {
  background: none;
  border: none;
  font-size: 1.2rem;
  cursor: pointer;
  position: absolute;
  top: 1rem;
  right: 1rem;
}
.notification-item {
  padding: 0.5rem;
  border-bottom: 1px solid #eee;
}
.notification-item:last-child {
  border-bottom: none;
}
.notification-content {
  font-size: 0.9rem;
  margin-bottom: 0.2rem;
}
.timestamp {
  font-size: 0.8rem;
  color: #888;
}
.no-notifications {
  text-align: center;
  color: #888;
  font-size: 0.9rem;
  padding: 1rem 0;
}
@keyframes fade-in-out { 0%,100% { opacity: 0; } 10%,90% { opacity: 1; } }
@keyframes slide-in {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}
</style>

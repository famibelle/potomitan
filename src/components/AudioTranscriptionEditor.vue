<template>
  <div class="app-container">
    <div class="sticky-header">
      <h2 class="title">Maké an Kréyòl Gwadloupéyen</h2>
      <div v-if="successMessage" class="toast">{{ successMessage }}</div>
      <div class="search-bar">
        <input
          v-model="searchQuery"
          type="text"
          placeholder="🔎Rechercher ..."
          class="search-input"
        />
      </div>


      <!-- Navigation rapide (SUPPRIMÉE du header) -->
      <!--
      <div class="navigation-controls" v-if="visibleFiles.length">
        <span class="nav-status">Segment {{ currentIndexDisplay + 1 }} / {{ audioFiles.length }}</span>
        <div class="nav-btn-group">
          <button @click="shuffleFiles" class="nav-btn" title="Mélanger l'ordre des fichiers">🔀</button>
          <button @click="sortByLikes" class="nav-btn" title="Trier par nombre de likes">👍🏿</button>
          <button @click="sortByDislikes" class="nav-btn" title="Trier par nombre de dislikes">👎🏿</button>
          <button @click="sortByStars" class="nav-btn" title="Trier par nombre d'étoiles (cliquer à nouveau pour inverser)">★</button>
          <button class="nav-btn" title="Notifications" @click="toggleNotifications">🔔<span class="notification-badge">{{ notificationCount }}</span> </button>
        </div>
      </div>
      -->
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
      


      <!-- Zone de saisie et bouton Valider -->
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
          <span v-if="notif.timestamp" class="notif-time"> le {{ new Date(notif.timestamp).toLocaleString('fr-FR', {
              day: 'numeric',
              month: 'long',
              hour: '2-digit',
              minute: '2-digit',
              hour12: false
            }).replace(':', 'h') }}
          </span>
        </template>
        <template v-else-if="notif.type === 'dislike'">
          👎🏿 Nouveau dislike sur <b>{{ notif.fileName }}</b>
          <span v-if="notif.timestamp" class="notif-time"> le {{ new Date(notif.timestamp).toLocaleString('fr-FR', {
              day: 'numeric',
              month: 'long',
              hour: '2-digit',
              minute: '2-digit',
              hour12: false
            }).replace(':', 'h') }}
          </span>
        </template>
        <template v-else-if="notif.type === 'transcription'">
          📝 Nouvelle transcription sur <b>{{ notif.fileName }}</b>
          <span v-if="notif.timestamp" class="notif-time"> le {{ new Date(notif.timestamp).toLocaleString('fr-FR', {
              day: 'numeric',
              month: 'long',
              hour: '2-digit',
              minute: '2-digit',
              hour12: false
            }).replace(':', 'h') }}
          </span>
          <div class="notif-content">"{{ notif.content }}"</div>
        </template>
        <template v-else-if="notif.type === 'rating'">
          ⭐ Note modifiée sur <b>{{ notif.fileName }}</b> : {{ notif.newRating }}
          <span v-if="notif.timestamp" class="notif-time"> le {{ new Date(notif.timestamp).toLocaleString('fr-FR', {
              day: 'numeric',
              month: 'long',
              hour: '2-digit',
              minute: '2-digit',
              hour12: false
            }).replace(':', 'h') }}
          </span>
        </template>
      </div>
    </div>

    <!-- Sticky footer avec les boutons de navigation et notifications -->
    <footer class="sticky-footer" v-if="visibleFiles.length">

      <span class="nav-status">
        <button @click="shuffleFiles" class="nav-btn" title="Mélanger l'ordre des fichiers">🔀</button>
        <button @click="jumpPrevious" class="nav-btn" title="Sauter 10 segments en arrière">⏮️</button>
        Segment {{ currentIndexDisplay + 1 }} / {{ audioFiles.length }}
        <button @click="jumpNext" class="nav-btn" title="Sauter 10 segments en avant">⏭️</button>
      </span>      
      
      <div class="nav-btn-group">
        <button @click="sortByStars" class="nav-btn" title="Trier par nombre d'étoiles (cliquer à nouveau pour inverser)">⭐</button>
        <button @click="sortByDate" class="nav-btn" title="Trier par date de création">🆕</button>
        <button class="nav-btn" title="Notifications" @click="toggleNotifications">
          🔔 <span class="notification-badge">{{ notificationCount }}</span>
        </button>
        <button 
          @click="toggleLikeDislike" 
          class="nav-btn" 
          :title="likeDislikeState === 'like' ? 'Trier par likes' : 'Trier par dislikes'"
        >
          {{ likeDislikeState === 'like' ? '👍🏿' : '👎🏿' }}
        </button>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, computed, nextTick, watch } from 'vue'

const searchQuery = ref('');
const audioFiles = ref([]); // tous les fichiers

function getFilteredSource() {
  if (!searchQuery.value.trim()) return audioFiles.value;
  const q = searchQuery.value.toLowerCase();
  return audioFiles.value.filter(f =>
    (f.transcription || '').toLowerCase().includes(q)
  );
}

const visibleFiles = ref([]);
let currentIndex = 0;
const BATCH_SIZE = 5;

function loadMore() {
  const source = getFilteredSource();
  const nextBatch = source.slice(currentIndex, currentIndex + BATCH_SIZE);
  visibleFiles.value.push(...nextBatch);
  currentIndex += BATCH_SIZE;
}

// Reset visibleFiles et currentIndex à chaque changement de recherche
watch(searchQuery, () => {
  visibleFiles.value = [];
  currentIndex = 0;
  loadMore();
});

const textareas = {}
const audioRefs = {}
const currentFocusedId = ref(null)
const showNotifications = ref(false);
const successMessage = ref('')

const currentIndexDisplay = computed(() => {
  const id = currentFocusedId.value
  const idx = audioFiles.value.findIndex(f => f.id === id)
  return idx >= 0 ? idx : 0
})

const hasPrevious = computed(() => currentIndexDisplay.value > 0)
const hasNext = computed(() => currentIndexDisplay.value < audioFiles.value.length - 1)

const filteredFiles = computed(() => {
  if (!searchQuery.value.trim()) return visibleFiles.value
  const q = searchQuery.value.toLowerCase()
  return visibleFiles.value.filter(f =>
    (f.transcription || '').toLowerCase().includes(q)
  )
})

function goToPrevious() {
  const prev = audioFiles.value[currentIndexDisplay.value - 1]
  if (prev) focusTextarea(prev.id)
}

function goToNext() {
  const next = audioFiles.value[currentIndexDisplay.value + 1]
  if (next) focusTextarea(next.id)
}

function jumpPrevious() {
  const total = audioFiles.value.length;
  let targetIdx = (currentIndexDisplay.value - 10 + total) % total;
  showOnlyBatchContaining(targetIdx);
  const file = audioFiles.value[targetIdx];
  if (file) focusTextarea(file.id);
}

function jumpNext() {
  const total = audioFiles.value.length;
  let targetIdx = (currentIndexDisplay.value + 10) % total;
  showOnlyBatchContaining(targetIdx);
  const file = audioFiles.value[targetIdx];
  if (file) focusTextarea(file.id);
}

function showOnlyBatchContaining(targetIdx) {
  const start = Math.floor(targetIdx / BATCH_SIZE) * BATCH_SIZE;
  const end = Math.min(start + BATCH_SIZE, audioFiles.value.length);
  visibleFiles.value = audioFiles.value.slice(start, end);
  currentIndex = end;
}
  
// S'assure que le segment ciblé est chargé et visible
function ensureVisible(targetIdx) {
  // Si le fichier n'est pas encore visible, on charge les batchs nécessaires
  while (!visibleFiles.value.includes(audioFiles.value[targetIdx]) && currentIndex < targetIdx + 1) {
    loadMore();
  }
}

function formatNotifDatetime(dateStr) {
  const date = new Date(dateStr);
  const mois = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre"
  ];
  return `${date.getDate()} ${mois[date.getMonth()]} à ${date.getHours()}h${date.getMinutes().toString().padStart(2, '0')}`;
}
  
function focusTextarea(id) {
  nextTick(() => {
    const el = textareas[id]
    if (el) el.focus()
    currentFocusedId.value = id
  })
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

const dateSortAsc = ref(false); // État pour l'ordre croissant/décroissant

function sortByDate() {
  console.log("🆕 sortByDate called, asc =", dateSortAsc.value);
  audioFiles.value.sort((a, b) => {
    // On essaie d'abord camelCase, puis snake_case
    const dateA = new Date(a.createdAt || a.created_at || 0);
    const dateB = new Date(b.createdAt || b.created_at || 0);
    return dateB - dateA;
  });
  dateSortAsc.value = !dateSortAsc.value;
  // Recharge tout ou, au moins, plus de fichiers pour voir le tri
  visibleFiles.value = [];
  currentIndex = 0;
  // Pour debug, vous pouvez temporairement :
  // BATCH_SIZE = audioFiles.value.length 
  // ou remplacer loadMore() par :
  // visibleFiles.value = [...audioFiles.value];
  loadMore();
}

const languages    = ref([])
const methods      = ref([])
const statuses     = ref([])
const contributors = ref([])

onMounted(async () => {
  // Chargement des dimensions
  const [langRes, methRes, statRes, contRes] = await Promise.all([
    fetch('/api/dim-languages'),
    fetch('/api/dim-methods'),
    fetch('/api/dim-statuses'),
    fetch('/api/contributors')
  ])
  languages.value    = await langRes.json()
  methods.value      = await methRes.json()
  statuses.value     = await statRes.json()
  contributors.value = await contRes.json()

  // Tri par created_at décroissant (plus récent en premier)
  audioFiles.value.sort((a, b) => {
    const dateA = new Date(a.createdAt || a.created_at || 0);
    const dateB = new Date(b.createdAt || b.created_at || 0);
    return dateB - dateA;
  });

  visibleFiles.value = [];
  currentIndex = 0;
  loadMore();
  window.addEventListener('scroll', handleScroll, { passive: true });
  window.addEventListener('keydown', handleKeydown);
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

// État pour alterner l'ordre du tri
const interactionsSortAsc = ref(false);

// Fonction pour obtenir le timestamp de la dernière interaction
function getLastInteractionTimestamp(file) {
  const historyTs = file.history?.map(e => new Date(e.timestamp).getTime()) || [];
  const notifTs = notifications.value
    .filter(n => n.fileId === file.id)
    .map(n => new Date(n.timestamp).getTime());
  const allTs = [...historyTs, ...notifTs];
  if (allTs.length) return Math.max(...allTs);
  return new Date(file.timestamp || file.createdAt || 0).getTime();
}

// Fonction pour trier par interactions
function sortByInteractions() {
  audioFiles.value.sort((a, b) => {
    const ta = getLastInteractionTimestamp(a);
    const tb = getLastInteractionTimestamp(b);
    return interactionsSortAsc.value ? ta - tb : tb - ta;
  });
  interactionsSortAsc.value = !interactionsSortAsc.value;
  visibleFiles.value = [];
  currentIndex = 0;
  loadMore();
}

// État pour alterner entre like et dislike
const likeDislikeState = ref('like'); // Par défaut, commence par "like"

// Fonction pour alterner entre like et dislike
function toggleLikeDislike() {
  likeDislikeState.value = likeDislikeState.value === 'like' ? 'dislike' : 'like';

  // Trier les fichiers en fonction de l'état actuel
  audioFiles.value.sort((a, b) => {
    const aLikes = a.likes || 0;
    const aDislikes = a.dislikes || 0;
    const bLikes = b.likes || 0;
    const bDislikes = b.dislikes || 0;

    if (likeDislikeState.value === 'like') {
      return bLikes - aLikes; // Trier par nombre de likes (descendant)
    } else {
      return bDislikes - aDislikes; // Trier par nombre de dislikes (descendant)
    }
  });

  // Mettre à jour les fichiers visibles
  visibleFiles.value = [];
  currentIndex = 0;
  loadMore();
}

function toggleOrder() {
  audioFiles.value.reverse(); // Inverse l'ordre des fichiers
  visibleFiles.value = [];
  currentIndex = 0;
  loadMore(); // Recharge les fichiers visibles
}

async function validate(id) {
  const file = visibleFiles.value.find(f => f.id === id)
  const payload = {
    name: file.name,
    transcription: file.transcription,
    langue_code: file.langue_code,
    methode_code: file.methode_code,
    statut_code: file.statut_code,
    id_contributeur: file.id_contributeur
  }
  const res = await fetch('/api/save-transcription', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
  try {
    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      if (res.status === 409 && data.error && data.error.includes('déjà été proposée')) {
        throw new Error('Cette transcription a déjà été proposée')
      }
      throw new Error(data.error || 'Erreur lors de la sauvegarde.')
    }
    if (!file.history) file.history = []
    file.history.push({ transcription: file.transcription, timestamp: new Date().toISOString() })
    // Afficher le toaster une seule fois
    if (!successMessage.value) {
      successMessage.value = `✅ Transcription « ${file.name} » validée !`
      setTimeout(() => (successMessage.value = ''), 3000)
    }
    await addNotification('transcription', file, { content: file.transcription });
  } catch (err) {
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
  const tag = document.activeElement.tagName
  if (e.code === 'Space' && tag !== 'TEXTAREA' && tag !== 'INPUT') {
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
  const res = await fetch('/api/audio-files');
  if (!res.ok) {
    console.error('Erreur HTTP', res.status, await res.text());
    throw new Error(`HTTP ${res.status}`);
  }

  const data = await res.json();
  // Génère l'URL de lecture à partir du nom de fichier
  audioFiles.value = data.map(file => ({
    ...file,
    url: `/audio/${file.name}`  
  }))
  
  // Tri par created_at décroissant (plus récent en premier)
  audioFiles.value.sort((a, b) => {
    const dateA = new Date(a.createdAt || a.created_at || 0);
    const dateB = new Date(b.createdAt || b.created_at || 0);
    return dateB - dateA;
  });

  visibleFiles.value = [];
  currentIndex = 0;
  loadMore();
  window.addEventListener('scroll', handleScroll, { passive: true });
  window.addEventListener('keydown', handleKeydown);
})

onBeforeUnmount(() => {
  window.removeEventListener('scroll', handleScroll)
  window.removeEventListener('keydown', handleKeydown)
})


  // Trier les fichiers en fonction de l'état actuel
  audioFiles.value.sort((a, b) => {
    const aLikes = a.likes || 0;
    const aDislikes = a.dislikes || 0;
    const bLikes = b.likes || 0;
    const bDislikes = b.dislikes || 0;

    if (likeDislikeState.value === 'like') {
      return bLikes - aLikes; // Trier par nombre de likes (descendant)
    } else {
      return bDislikes - aDislikes; // Trier par nombre de dislikes (descendant)
    }
  });

  // Mettre à jour les fichiers visibles
  visibleFiles.value = [];
  currentIndex = 0;
  loadMore();


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
.sticky-footer {
  position: fixed;
  bottom: 0;
  left: 0;
  width: 100vw;
  background: #222; /* fond sombre */
  box-shadow: 0 -2px 8px rgba(0,0,0,0.18);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 1rem 0.5rem;
  z-index: 1001;
  border-top: 1px solid #333;
}

.sticky-footer .nav-status {
  color: #fff;
  font-weight: 500;
  margin-bottom: 0.5rem;
}

.sticky-footer .nav-btn-group {
  display: flex;
  gap: 1.2rem;
}

.sticky-footer .nav-btn {
  background: none;
  border: none;
  color: #fff;
  font-size: 1.5rem;
  cursor: pointer;
  transition: color 0.2s;
  position: relative; /* Pour positionner le badge */
}
.sticky-footer .nav-btn:hover {
  color: #ffd700;
}

/* Badge notification plus petit et positionné en haut à droite de la cloche */
.notification-badge {
  position: absolute;
  top: -1px;
  right: 2px;
  background: #e74c3c;
  color: #fff;
  border-radius: 50%;
  width: 24px;
  height: 24px;
  padding: 0;
  font-size: 0.75em;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
  font-weight: bold;
  box-shadow: 0 1px 4px rgba(0,0,0,0.15);
  z-index: 2;
}
.search-bar {
  margin: 1rem 0 2rem; /* Ajoute une marge en bas de 2rem */
  display: flex;
  justify-content: center;
}
.search-input {
  width: 100%;
  max-width: 400px;
  padding: 0.5rem 1rem;
  border: none !important; /* Supprime la bordure */
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 1rem;
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

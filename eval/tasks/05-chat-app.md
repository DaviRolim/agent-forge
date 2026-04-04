Build a real-time chat application with both frontend and backend:

**Backend:**
- WebSocket server for real-time message delivery
- REST endpoints: GET /api/conversations (list), GET /api/conversations/:id/messages (history), POST /api/conversations/:id/messages (send)
- In-memory storage (no database needed)
- Seed with 5 mock conversations with realistic message history (10-15 messages each)
- Simulate "other user" responses: after receiving a message, reply automatically after 2-3 seconds with a contextual response

**Frontend:**
- Sidebar showing 5 conversations with last message preview, timestamp, and unread count badge
- Main chat area with message bubbles (sent = right/blue, received = left/gray)
- Message input with send button and Enter key support
- Typing indicator animation when the simulated user is "typing"
- Auto-scroll to newest message on send and receive
- Timestamp separators ("Today", "Yesterday")
- Online/offline status indicator per conversation

**Real-time:**
- Messages appear instantly for sender
- Simulated responses arrive via WebSocket with typing indicator first
- Unread count updates in sidebar when receiving messages in non-active conversations

## Design Constraints
- Stack: SvelteKit (latest, Svelte 5 runes) + Tailwind CSS
- Mobile-first, responsive (sidebar collapses to drawer on mobile)
- Chat bubble styling should feel like iMessage/WhatsApp — familiar, not corporate
- Smooth animations throughout (transitions, message appear, typing dots)
- Premium feel — this should look like a real product, not a tutorial project

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  Box, Button, Card, CardContent, Chip, Container, Divider, FormControl,
  Grid, IconButton, InputLabel, List, ListItemButton, ListItemText,
  MenuItem, Paper, Select, TextField, Typography,
} from '@mui/material';
import { supabase } from '../../lib/supabase';
import { useAuth } from '../../contexts/AuthContext';

interface Conversation {
  id: string;
  title: string;
  agent: string;
  updated_at: string;
}

interface Message {
  id: string;
  role: string;
  content: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

const AGENTS = ['architect', 'backend-dev', 'frontend-dev', 'reviewer', 'tester'];

const QUICK_ACTIONS = [
  { label: '📋 Review code', prompt: 'Review the recent changes in this codebase' },
  { label: '🏗️ Plan feature', prompt: 'Plan the implementation for: ' },
  { label: '📁 Browse files', prompt: 'List the project structure and key files' },
  { label: '🧪 Run tests', prompt: 'Run the test suite and report results' },
];

export default function Chat() {
  const { user } = useAuth();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConvo, setActiveConvo] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [agent, setAgent] = useState('architect');
  const [streaming, setStreaming] = useState(false);
  const [streamText, setStreamText] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);

  // Load conversations
  const loadConversations = useCallback(async () => {
    const { data } = await supabase
      .from('conversations')
      .select('*')
      .order('updated_at', { ascending: false });
    if (data) setConversations(data);
  }, []);

  // Load messages for active conversation
  const loadMessages = useCallback(async (convoId: string) => {
    const { data } = await supabase
      .from('messages')
      .select('*')
      .eq('conversation_id', convoId)
      .order('created_at');
    if (data) setMessages(data);
  }, []);

  useEffect(() => { loadConversations(); }, [loadConversations]);

  useEffect(() => {
    if (activeConvo) {
      loadMessages(activeConvo);
      // Realtime subscription
      const ch = supabase
        .channel(`messages-${activeConvo}`)
        .on('postgres_changes', {
          event: 'INSERT', schema: 'public', table: 'messages',
          filter: `conversation_id=eq.${activeConvo}`,
        }, () => loadMessages(activeConvo))
        .subscribe();
      return () => { supabase.removeChannel(ch); };
    }
    return undefined;
  }, [activeConvo, loadMessages]);

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamText]);

  const createConversation = async () => {
    if (!user) return;
    const { data } = await supabase
      .from('conversations')
      .insert({ user_id: user.id, agent, title: 'New Chat' })
      .select()
      .single();
    if (data) {
      setActiveConvo(data.id);
      loadConversations();
    }
  };

  const sendMessage = async (content: string) => {
    if (!content.trim() || !activeConvo) return;

    setInput('');
    setStreaming(true);
    setStreamText('');

    // Connect WebSocket
    const wsUrl = `ws://localhost:8000/ws/chat/${activeConvo}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      ws.send(JSON.stringify({ content, agent }));
    };

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.type === 'token') {
        setStreamText((prev) => prev + msg.content);
      } else if (msg.type === 'done') {
        setStreaming(false);
        setStreamText('');
        loadMessages(activeConvo);
        loadConversations();
      } else if (msg.type === 'thinking') {
        setStreamText('Thinking...');
      }
    };

    ws.onerror = () => {
      setStreaming(false);
      setStreamText('Connection error');
    };

    // Save user message immediately for display
    setMessages((prev) => [...prev, {
      id: crypto.randomUUID(),
      role: 'user',
      content,
      metadata: {},
      created_at: new Date().toISOString(),
    }]);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  return (
    <Box sx={{ display: 'flex', height: 'calc(100vh - 64px)' }}>
      {/* Conversation List — Left Sidebar */}
      <Box
        sx={{
          width: 280, borderRight: 1, borderColor: 'divider',
          display: 'flex', flexDirection: 'column', bgcolor: 'background.paper',
        }}
        data-testid="conversation-list"
      >
        <Box sx={{ p: 2 }}>
          <Button
            variant="contained"
            fullWidth
            onClick={createConversation}
            data-testid="new-chat-btn"
          >
            New Chat
          </Button>
        </Box>
        <List sx={{ flex: 1, overflow: 'auto', px: 1 }}>
          {conversations.map((c) => (
            <ListItemButton
              key={c.id}
              selected={c.id === activeConvo}
              onClick={() => setActiveConvo(c.id)}
              sx={{ borderRadius: 1, mb: 0.5 }}
              data-testid={`convo-${c.id}`}
            >
              <ListItemText
                primary={c.title}
                secondary={c.agent}
                primaryTypographyProps={{ noWrap: true, variant: 'body2' }}
                secondaryTypographyProps={{ variant: 'caption' }}
              />
            </ListItemButton>
          ))}
        </List>
      </Box>

      {/* Chat Area — Right */}
      <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        {/* Agent selector */}
        <Box sx={{ p: 1.5, borderBottom: 1, borderColor: 'divider', display: 'flex', gap: 2, alignItems: 'center' }}>
          <FormControl size="small" sx={{ minWidth: 160 }} data-testid="agent-selector">
            <InputLabel>Agent</InputLabel>
            <Select value={agent} label="Agent" onChange={(e) => setAgent(e.target.value)}>
              {AGENTS.map((a) => <MenuItem key={a} value={a}>{a}</MenuItem>)}
            </Select>
          </FormControl>
          <Box display="flex" gap={0.5}>
            {QUICK_ACTIONS.map((qa) => (
              <Chip
                key={qa.label}
                label={qa.label}
                size="small"
                variant="outlined"
                onClick={() => sendMessage(qa.prompt)}
                sx={{ cursor: 'pointer' }}
                data-testid={`quick-${qa.label.slice(3).toLowerCase().replace(/\s/g, '-')}`}
              />
            ))}
          </Box>
        </Box>

        {/* Messages */}
        <Box sx={{ flex: 1, overflow: 'auto', p: 2 }} data-testid="message-thread">
          {!activeConvo && (
            <Box sx={{ textAlign: 'center', mt: 10 }}>
              <Typography variant="h5" color="text.secondary" sx={{ fontFamily: '"Fira Code"' }}>
                Agent Fleet Chat
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                Start a new conversation or select one from the sidebar.
              </Typography>
            </Box>
          )}

          {messages.map((msg) => (
            <Box
              key={msg.id}
              sx={{
                display: 'flex',
                justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
                mb: 2,
              }}
              data-testid={`msg-${msg.role}`}
            >
              <Paper
                sx={{
                  p: 2,
                  maxWidth: '70%',
                  bgcolor: msg.role === 'user' ? 'primary.main' : 'background.paper',
                  color: msg.role === 'user' ? '#fff' : 'text.primary',
                }}
              >
                {msg.role !== 'user' && (
                  <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
                    {(msg.metadata as Record<string, string>)?.agent || agent}
                  </Typography>
                )}
                <Typography
                  variant="body2"
                  sx={{
                    whiteSpace: 'pre-wrap',
                    fontFamily: msg.content.includes('```') ? '"Fira Code", monospace' : 'inherit',
                  }}
                >
                  {msg.content}
                </Typography>
              </Paper>
            </Box>
          ))}

          {/* Streaming response */}
          {streaming && streamText && (
            <Box sx={{ display: 'flex', justifyContent: 'flex-start', mb: 2 }}>
              <Paper sx={{ p: 2, maxWidth: '70%', bgcolor: 'background.paper' }}>
                <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
                  {agent}
                </Typography>
                <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                  {streamText}
                  <Box component="span" sx={{
                    display: 'inline-block', width: 8, height: 16,
                    bgcolor: 'primary.main', ml: 0.5,
                    animation: 'blink 1s infinite',
                    '@keyframes blink': { '0%, 100%': { opacity: 1 }, '50%': { opacity: 0 } },
                  }} />
                </Typography>
              </Paper>
            </Box>
          )}

          <div ref={messagesEndRef} />
        </Box>

        {/* Input */}
        <Box sx={{ p: 2, borderTop: 1, borderColor: 'divider' }}>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <TextField
              fullWidth
              multiline
              maxRows={4}
              placeholder={activeConvo ? 'Type a message...' : 'Create a conversation first'}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={!activeConvo || streaming}
              size="small"
              data-testid="chat-input"
            />
            <Button
              variant="contained"
              onClick={() => sendMessage(input)}
              disabled={!input.trim() || !activeConvo || streaming}
              data-testid="send-btn"
            >
              Send
            </Button>
          </Box>
        </Box>
      </Box>
    </Box>
  );
}

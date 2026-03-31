import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box, Button, Card, CardActionArea, CardContent, Chip, Container,
  Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle,
  Grid, IconButton, Step, StepLabel, Stepper, TextField, Tooltip, Typography,
} from '@mui/material';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import EditOutlinedIcon from '@mui/icons-material/EditOutlined';
import { supabase } from '../../lib/supabase';
import { useAuth } from '../../contexts/AuthContext';

interface Project {
  id: string;
  name: string;
  repo_path: string;
  languages: string[];
  frameworks: string[];
  test_frameworks: string[];
  estimated_loc: number;
  created_at: string;
}

const WIZARD_STEPS = ['Repository', 'Detected Stack', 'Agents', 'Confirm'];

export default function Projects() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [projects, setProjects] = useState<Project[]>([]);
  const [wizardOpen, setWizardOpen] = useState(false);
  const [activeStep, setActiveStep] = useState(0);
  const [repoPath, setRepoPath] = useState('');

  // Edit state
  const [editProject, setEditProject] = useState<Project | null>(null);
  const [editName, setEditName] = useState('');

  // Delete state
  const [deleteProject, setDeleteProject] = useState<Project | null>(null);

  const load = async () => {
    const { data } = await supabase.from('projects').select('*').order('created_at', { ascending: false });
    if (data) setProjects(data);
  };

  useEffect(() => { load(); }, []);

  const handleSave = async () => {
    if (!user) return;
    await supabase.from('projects').insert({
      user_id: user.id,
      name: repoPath.split('/').pop() || 'project',
      repo_path: repoPath,
      languages: ['python'],
      frameworks: ['fastapi'],
    });
    setWizardOpen(false);
    setActiveStep(0);
    setRepoPath('');
    load();
  };

  const handleEditSave = async () => {
    if (!editProject || !editName.trim()) return;
    await supabase.from('projects').update({ name: editName.trim() }).eq('id', editProject.id);
    setEditProject(null);
    load();
  };

  const handleDelete = async () => {
    if (!deleteProject) return;
    await supabase.from('projects').delete().eq('id', deleteProject.id);
    setDeleteProject(null);
    load();
  };

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" data-testid="projects-title">Projects</Typography>
        <Button variant="contained" onClick={() => setWizardOpen(true)} data-testid="add-project-btn">
          Add Project
        </Button>
      </Box>

      <Grid container spacing={2}>
        {projects.map((p) => (
          <Grid size={{ xs: 12, sm: 6, md: 4 }} key={p.id}>
            <Card data-testid={`project-card-${p.name}`} sx={{ position: 'relative' }}>
              <CardActionArea onClick={() => navigate(`/projects/${p.id}`)} data-testid={`project-card-link-${p.name}`}>
                <CardContent sx={{ pb: '40px !important' }}>
                  <Typography variant="h6" sx={{ fontFamily: '"Fira Code"' }}>{p.name}</Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>{p.repo_path}</Typography>
                  <Box display="flex" gap={0.5} flexWrap="wrap">
                    {p.languages?.map((l) => <Chip key={l} label={l} size="small" color="primary" />)}
                    {p.frameworks?.map((f) => <Chip key={f} label={f} size="small" variant="outlined" />)}
                  </Box>
                  {p.estimated_loc > 0 && (
                    <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                      ~{p.estimated_loc.toLocaleString()} LOC
                    </Typography>
                  )}
                </CardContent>
              </CardActionArea>
              {/* Action buttons — outside CardActionArea to avoid nested interactive elements */}
              <Box sx={{ position: 'absolute', bottom: 6, right: 6, display: 'flex', gap: 0.5 }}>
                <Tooltip title="Rename">
                  <IconButton
                    size="small"
                    data-testid={`edit-project-${p.name}`}
                    onClick={(e) => { e.stopPropagation(); setEditProject(p); setEditName(p.name); }}
                  >
                    <EditOutlinedIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
                <Tooltip title="Delete">
                  <IconButton
                    size="small"
                    color="error"
                    data-testid={`delete-project-${p.name}`}
                    onClick={(e) => { e.stopPropagation(); setDeleteProject(p); }}
                  >
                    <DeleteOutlineIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
              </Box>
            </Card>
          </Grid>
        ))}
        {projects.length === 0 && (
          <Grid size={{ xs: 12 }}>
            <Typography color="text.secondary" align="center" data-testid="no-projects">
              No projects yet. Add one to get started.
            </Typography>
          </Grid>
        )}
      </Grid>

      {/* Onboarding Wizard */}
      <Dialog open={wizardOpen} onClose={() => setWizardOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Add Project</DialogTitle>
        <DialogContent>
          <Stepper activeStep={activeStep} sx={{ mb: 3 }} data-testid="wizard-stepper">
            {WIZARD_STEPS.map((label) => (
              <Step key={label}><StepLabel>{label}</StepLabel></Step>
            ))}
          </Stepper>

          {activeStep === 0 && (
            <TextField
              label="Repository Path"
              fullWidth
              value={repoPath}
              onChange={(e) => setRepoPath(e.target.value)}
              placeholder="/path/to/project or https://github.com/org/repo"
              data-testid="wizard-repo-input"
            />
          )}
          {activeStep === 1 && (
            <Box data-testid="wizard-stack">
              <Typography variant="subtitle2">Detected Stack</Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                Scanning will be available when connected to the fleet init API.
                For now, the project will be saved with default detection.
              </Typography>
            </Box>
          )}
          {activeStep === 2 && (
            <Box data-testid="wizard-agents">
              <Typography variant="subtitle2">Recommended Agents</Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                Default agents will be used. Customize via the Agent Builder after saving.
              </Typography>
            </Box>
          )}
          {activeStep === 3 && (
            <Box data-testid="wizard-confirm">
              <Typography variant="subtitle2">Confirm</Typography>
              <Typography variant="body2" sx={{ mt: 1 }}>
                Project: <strong>{repoPath.split('/').pop()}</strong>
              </Typography>
              <Typography variant="body2">Path: {repoPath}</Typography>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setWizardOpen(false)}>Cancel</Button>
          {activeStep > 0 && (
            <Button onClick={() => setActiveStep((s) => s - 1)}>Back</Button>
          )}
          {activeStep < WIZARD_STEPS.length - 1 ? (
            <Button variant="contained" onClick={() => setActiveStep((s) => s + 1)}
              disabled={activeStep === 0 && !repoPath} data-testid="wizard-next">
              Next
            </Button>
          ) : (
            <Button variant="contained" onClick={handleSave} data-testid="wizard-save">
              Save Project
            </Button>
          )}
        </DialogActions>
      </Dialog>

      {/* Edit Dialog */}
      <Dialog open={!!editProject} onClose={() => setEditProject(null)} maxWidth="xs" fullWidth>
        <DialogTitle>Rename Project</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            fullWidth
            label="Project Name"
            value={editName}
            onChange={(e) => setEditName(e.target.value)}
            sx={{ mt: 1 }}
            data-testid="edit-project-name-input"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditProject(null)}>Cancel</Button>
          <Button variant="contained" onClick={handleEditSave} disabled={!editName.trim()} data-testid="edit-project-save">
            Save
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={!!deleteProject} onClose={() => setDeleteProject(null)} maxWidth="xs" fullWidth>
        <DialogTitle>Delete Project</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to delete <strong>{deleteProject?.name}</strong>?
            Existing tasks will be unlinked but not deleted.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteProject(null)}>Cancel</Button>
          <Button variant="contained" color="error" onClick={handleDelete} data-testid="confirm-delete-project">
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
}

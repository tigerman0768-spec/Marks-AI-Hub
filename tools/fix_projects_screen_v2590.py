from pathlib import Path

p = Path("lib/film_projects_screen.dart")

p.write_text(r"""import 'package:flutter/material.dart';
import 'film_creator_project.dart';
import 'film_creator_offline_screen.dart';

class FilmProjectsScreen extends StatefulWidget {
  const FilmProjectsScreen({super.key});

  @override
  State<FilmProjectsScreen> createState() => _FilmProjectsScreenState();
}

class _FilmProjectsScreenState extends State<FilmProjectsScreen> {
  List<FilmCreatorProject> projects = <FilmCreatorProject>[];
  bool loading = true;

  @override
  void initState() {
    super.initState();
    _loadProjects();
  }

  Future<void> _loadProjects() async {
    final items = await FilmCreatorProject.allLocal();
    if (!mounted) return;
    setState(() {
      projects = items;
      loading = false;
    });
  }

  Future<void> _newProject() async {
    await Navigator.of(context).push(
      MaterialPageRoute(builder: (_) => const OfflineFilmCreatorScreen()),
    );
    await _loadProjects();
  }

  Future<void> _openProject(FilmCreatorProject project) async {
    await Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => OfflineFilmCreatorScreen(projectId: project.id),
      ),
    );
    await _loadProjects();
  }

  Future<void> _deleteProject(FilmCreatorProject project) async {
    await project.deleteLocal();
    await _loadProjects();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Projects'),
        actions: [
          IconButton(
            tooltip: 'Refresh',
            onPressed: _loadProjects,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _newProject,
        icon: const Icon(Icons.add),
        label: const Text('NEW PROJECT'),
      ),
      body: loading
          ? const Center(child: CircularProgressIndicator())
          : projects.isEmpty
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(Icons.movie_creation_outlined, size: 64),
                        const SizedBox(height: 16),
                        const Text(
                          'No saved projects yet',
                          style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                        ),
                        const SizedBox(height: 8),
                        const Text(
                          'Projects created in Film Creator are saved directly on this phone.',
                          textAlign: TextAlign.center,
                        ),
                        const SizedBox(height: 20),
                        FilledButton.icon(
                          onPressed: _newProject,
                          icon: const Icon(Icons.add),
                          label: const Text('CREATE PROJECT'),
                        ),
                      ],
                    ),
                  ),
                )
              : RefreshIndicator(
                  onRefresh: _loadProjects,
                  child: ListView.builder(
                    padding: const EdgeInsets.fromLTRB(12, 12, 12, 100),
                    itemCount: projects.length,
                    itemBuilder: (context, index) {
                      final project = projects[index];
                      return Card(
                        child: ListTile(
                          leading: const CircleAvatar(
                            child: Icon(Icons.movie),
                          ),
                          title: Text(project.title),
                          subtitle: Text(
                            project.genre + ' • ' + project.length.toString() + ' min • ' + project.aspectRatio,
                          ),
                          onTap: () => _openProject(project),
                          trailing: PopupMenuButton<String>(
                            onSelected: (value) {
                              if (value == 'open') _openProject(project);
                              if (value == 'delete') _deleteProject(project);
                            },
                            itemBuilder: (_) => const [
                              PopupMenuItem(
                                value: 'open',
                                child: Text('Open'),
                              ),
                              PopupMenuItem(
                                value: 'delete',
                                child: Text('Delete'),
                              ),
                            ],
                          ),
                        ),
                      );
                    },
                  ),
                ),
    );
  }
}
""")
print("Created Projects-screen repair script.")

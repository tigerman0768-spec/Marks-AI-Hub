from pathlib import Path

lib = Path("lib")

def write(name, body):
    (lib / name).write_text(body)

def replace(name, old, new):
    f = lib / name
    s = f.read_text()
    if old not in s:
        print("pattern not found:", name)
        return
    f.write_text(s.replace(old, new))

write("film_creator_project.dart", r"""import 'dart:convert';
import 'dart:io';
import 'package:path_provider/path_provider.dart';
import 'package:uuid/uuid.dart';

class FilmCreatorProject {
  final Map<String, dynamic> state;
  FilmCreatorProject(this.state);

  String get id => state['id']?.toString() ?? '';
  String get title => state['title']?.toString() ?? 'Untitled Film';
  String get idea => state['idea']?.toString() ?? '';
  String get genre => state['genre']?.toString() ?? 'Drama';
  int get length => int.tryParse(state['length']?.toString() ?? '5') ?? 5;
  String get style => state['style']?.toString() ?? 'Cinematic';
  String get aspectRatio => state['aspectRatio']?.toString() ?? '16:9';

  static Future<Directory> _dir() async {
    final root = await getApplicationDocumentsDirectory();
    final dir = Directory('${root.path}/marks_ai_projects');
    if (!await dir.exists()) await dir.create(recursive: true);
    return dir;
  }

  static Future<File> _file(String id) async {
    final dir = await _dir();
    final safe = id.replaceAll(RegExp(r'[^A-Za-z0-9_-]'), '_');
    return File('${dir.path}/${safe}.json');
  }

  static Future<FilmCreatorProject?> resume(String id) async {
    try {
      final f = await _file(id);
      if (!await f.exists()) return null;
      final data = jsonDecode(await f.readAsString()) as Map;
      return FilmCreatorProject(Map<String, dynamic>.from(data));
    } catch (_) {
      return null;
    }
  }

  static Future<FilmCreatorProject> createLocal(Map<String, dynamic> state) async {
    final id = const Uuid().v4();
    final p = FilmCreatorProject({...state, 'id': id});
    await p._write();
    return p;
  }

  Future<FilmCreatorProject> saveLocal(Map<String, dynamic> changes) async {
    final p = FilmCreatorProject({...state, ...changes, 'id': id});
    await p._write();
    return p;
  }

  Future<void> _write() async {
    final f = await _file(id);
    await f.writeAsString(jsonEncode(state), flush: true);
  }

  static Future<List<FilmCreatorProject>> allLocal() async {
    final dir = await _dir();
    final result = <FilmCreatorProject>[];
    await for (final e in dir.list()) {
      if (e is! File || !e.path.endsWith('.json')) continue;
      try {
        final data = jsonDecode(await e.readAsString()) as Map;
        result.add(FilmCreatorProject(Map<String, dynamic>.from(data)));
      } catch (_) {}
    }
    result.sort((a, b) => a.title.toLowerCase().compareTo(b.title.toLowerCase()));
    return result;
  }

  Future<void> deleteLocal() async {
    try {
      final f = await _file(id);
      if (await f.exists()) await f.delete();
    } catch (_) {}
  }
}
""")

old_save = r"""  Future<void> _save({bool create=false}) async{
    setState(()=>saving=true);
    try{
      final body={'title':title.text.trim().isEmpty?'Untitled Film':title.text.trim(),'idea':idea.text.trim(),
        'genre':genre,'length':length,'style':style,'aspectRatio':aspect,'status':'draft'};
      if(projectId==null||create){
        final r=await http.post(Uri.parse('$base/api/projects'),headers:{'Content-Type':'application/json'},body:jsonEncode(body));
        if(r.statusCode<300){projectId=(jsonDecode(r.body) as Map)['id']?.toString();}
      }else{
        await http.put(Uri.parse('$base/api/projects/$projectId/creator-state'),
          headers:{'Content-Type':'application/json'},body:jsonEncode(body));
      }
      if(mounted)ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content:Text('Project saved')));
    }catch(e){
      if(mounted)ScaffoldMessenger.of(context).showSnackBar(SnackBar(content:Text('Save failed: $e')));
    }
    if(mounted)setState(()=>saving=false);
  }"""
new_save = r"""  Future<void> _save({bool create=false}) async{
    setState(()=>saving=true);
    try{
      final body={'title':title.text.trim().isEmpty?'Untitled Film':title.text.trim(),'idea':idea.text.trim(),
        'genre':genre,'length':length,'style':style,'aspectRatio':aspect,'status':'draft'};
      if(projectId==null||create){
        final p=await FilmCreatorProject.createLocal(body);
        projectId=p.id;
      }else{
        await FilmCreatorProject({'id':projectId!, ...body}).saveLocal(body);
      }
      if(mounted)ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content:Text('Project saved on this phone')));
    }catch(e){
      if(mounted)ScaffoldMessenger.of(context).showSnackBar(SnackBar(content:Text('Local save failed: $e')));
    }
    if(mounted)setState(()=>saving=false);
  }"""
replace("film_creator_screen.dart", old_save, new_save)

write("film_projects_screen.dart", r"""import 'package:flutter/material.dart';
import 'film_creator_project.dart';

class FilmProjectsScreen extends StatefulWidget{
  final void Function(FilmCreatorProject project)? onResume;
  const FilmProjectsScreen({super.key,this.onResume});
  @override State<FilmProjectsScreen> createState()=>_FilmProjectsScreenState();
}

class _FilmProjectsScreenState extends State<FilmProjectsScreen>{
  List<FilmCreatorProject> projects=[]; bool loading=true;
  @override void initState(){super.initState();load();}

  Future<void> load() async{
    setState(()=>loading=true);
    projects=await FilmCreatorProject.allLocal();
    if(mounted)setState(()=>loading=false);
  }

  Future<void> createProject() async{
    final c=TextEditingController();
    final title=await showDialog<String>(
      context:context,
      builder:(_)=>AlertDialog(
        title:const Text('New film project'),
        content:TextField(controller:c,autofocus:true,decoration:const InputDecoration(hintText:'Film title')),
        actions:[
          TextButton(onPressed:()=>Navigator.pop(context),child:const Text('Cancel')),
          FilledButton(onPressed:()=>Navigator.pop(context,c.text.trim()),child:const Text('Create'))
        ],
      ),
    );
    c.dispose();
    if(title==null||title.isEmpty)return;
    await FilmCreatorProject.createLocal({
      'title':title,'idea':'','genre':'Drama','length':5,'style':'Cinematic','aspectRatio':'16:9','status':'draft'
    });
    await load();
  }

  Future<void> remove(FilmCreatorProject p) async{
    final ok=await showDialog<bool>(
      context:context,
      builder:(_)=>AlertDialog(
        title:const Text('Delete project?'),
        content:Text('Delete "${p.title}"?'),
        actions:[
          TextButton(onPressed:()=>Navigator.pop(context),child:const Text('Cancel')),
          FilledButton(onPressed:()=>Navigator.pop(context,true),child:const Text('Delete'))
        ],
      ),
    );
    if(ok==true){await p.deleteLocal();await load();}
  }

  void resume(FilmCreatorProject p){
    if(widget.onResume!=null){widget.onResume!(p);return;}
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content:Text('Loaded "${p.title}"')));
  }

  @override Widget build(BuildContext context)=>Scaffold(
    appBar:AppBar(title:const Text('Film Projects'),actions:[IconButton(onPressed:load,icon:const Icon(Icons.refresh))]),
    floatingActionButton:FloatingActionButton.extended(onPressed:createProject,icon:const Icon(Icons.add),label:const Text('New Film')),
    body:loading?const Center(child:CircularProgressIndicator()):
      projects.isEmpty?const Center(child:Text('No saved projects yet.')):
      ListView.separated(
        padding:const EdgeInsets.all(12),itemCount:projects.length,
        separatorBuilder:(_,__)=>const SizedBox(height:8),
        itemBuilder:(context,i){
          final p=projects[i];
          return Card(child:ListTile(
            onTap:()=>resume(p),
            leading:const CircleAvatar(child:Icon(Icons.movie_outlined)),
            title:Text(p.title),
            subtitle:Text('${p.genre} • ${p.style} • ${p.length} min'),
            trailing:Wrap(mainAxisSize:MainAxisSize.min,children:[
              IconButton(tooltip:'Continue',icon:const Icon(Icons.play_arrow),onPressed:()=>resume(p)),
              IconButton(icon:const Icon(Icons.delete_outline),onPressed:()=>remove(p)),
            ]),
          ));
        },
      ),
  );
}
""")

replace(
  "film_creator_screen.dart",
  "    if (projectId == null) return;\n    if (!mounted) return;\n    setState(() => saving = true);",
  "    if (projectId == null) return;\n    if (!mounted) return;\n    ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Project saved locally. Online screenplay generation needs an optional backend.')));\n    return;\n    // Online generation is intentionally disabled in the free offline build.\n    setState(() => saving = true);"
)

import 'approved_shots_screen.dart';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'video_generation_screen.dart';

class ShotCardsScreen extends StatefulWidget{
  final String projectId;
  const ShotCardsScreen({super.key,required this.projectId});
  @override State<ShotCardsScreen> createState()=>_ShotCardsScreenState();
}
class _ShotCardsScreenState extends State<ShotCardsScreen>{
  static const base='http://10.0.2.2:3000';
  List<Map<String,dynamic>> shots=[]; bool loading=true;
  @override void initState(){super.initState();load();}
  Future<void> load() async{
    try{
      final r=await http.get(Uri.parse('$base/api/projects/${widget.projectId}/shot-cards'));
      if(r.statusCode==200){
        final d=jsonDecode(r.body) as Map<String,dynamic>;
        shots=(d['shots'] as List? ?? []).map((e)=>Map<String,dynamic>.from(e)).toList();
      }
    }catch(_){}
    if(mounted)setState(()=>loading=false);
  }
  Widget line(String label,dynamic value)=>Padding(
    padding:const EdgeInsets.only(top:4),
    child:Text('$label: ${value??'TBD'}'));
  @override Widget build(BuildContext context){
    if(loading)return const Scaffold(body:Center(child:CircularProgressIndicator()));
    return Scaffold(appBar:AppBar(title:const Text('Shot Cards')),body:shots.isEmpty
      ?const Center(child:Text('Generate a storyboard first.'))
      :Column(children:[
        Padding(padding:const EdgeInsets.all(12),child:FilledButton.icon(
          onPressed:()=>Navigator.push(context,MaterialPageRoute(builder:(_)=>VideoGenerationScreen(projectId:widget.projectId))),
          icon:const Icon(Icons.movie_creation),label:const Text('GENERATE VIDEO CLIPS'))),
        Expanded(child:ListView.builder(padding:const EdgeInsets.fromLTRB(12,0,12,12),itemCount:shots.length,itemBuilder:(context,i){
        final s=shots[i];
        return Card(margin:const EdgeInsets.only(bottom:10),child:ExpansionTile(
          leading:CircleAvatar(child:Text('${s['shotNumber']??i+1}')),
          title:Text('${s['sceneTitle']??'Scene'} • ${s['shotType']??'shot'}'),
          subtitle:Text(s['cameraMovement']?.toString()??''),
          childrenPadding:const EdgeInsets.fromLTRB(16,0,16,16),
          children:[
            line('Purpose',s['purpose']),line('Emotion',s['emotion']),line('Lighting',s['lighting']),
            line('Characters',((s['continuity']?['preserveCharacters'] as List?)??[]).join(', ')),
            line('Location',s['continuity']?['preserveLocation']),
            line('Wardrobe',s['continuity']?['wardrobe']),
            const SizedBox(height:8),Align(alignment:Alignment.centerLeft,child:
              Text('Generation prompt',style:Theme.of(context).textTheme.titleMedium)),
            Align(alignment:Alignment.centerLeft,child:Text(s['prompt']?.toString()??'')),
          ]));
      })),]) ;
  }
}

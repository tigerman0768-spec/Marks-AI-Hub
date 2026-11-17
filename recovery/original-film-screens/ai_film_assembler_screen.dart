import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

class AiFilmAssemblerScreen extends StatefulWidget{
  final String projectId;
  const AiFilmAssemblerScreen({super.key,required this.projectId});
  @override State<AiFilmAssemblerScreen> createState()=>_AiFilmAssemblerScreenState();
}
class _AiFilmAssemblerScreenState extends State<AiFilmAssemblerScreen>{
  static const base='http://10.0.2.2:3000';
  bool loading=false; Map<String,dynamic>? result;
  Future<void> assemble()async{
    setState(()=>loading=true);
    try{
      final r=await http.post(Uri.parse('$base/api/projects/${widget.projectId}/ai-assemble'));
      if(r.statusCode<300){
        setState(()=>result=Map<String,dynamic>.from(jsonDecode(r.body)));
        if(mounted)ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content:Text('AI film assembled')));
      }
    }catch(_){}
    if(mounted)setState(()=>loading=false);
  }
  @override Widget build(BuildContext context){
    return Scaffold(appBar:AppBar(title:const Text('AI Film Assembly')),
      body:Center(child:Padding(padding:const EdgeInsets.all(20),child:Column(
        mainAxisAlignment:MainAxisAlignment.center,children:[
          const Icon(Icons.movie_creation,size:72),
          const SizedBox(height:16),
          Text('Assemble the edited clips into one film.',
            style:Theme.of(context).textTheme.titleLarge,textAlign:TextAlign.center),
          const SizedBox(height:20),
          SizedBox(width:double.infinity,child:FilledButton.icon(
            onPressed:loading?null:assemble,icon:const Icon(Icons.play_arrow),
            label:Text(loading?'ASSEMBLING…':'ASSEMBLE AI FILM'))),
          if(result!=null) ...[
            const SizedBox(height:20),
            Text('${result!['clipCount']??0} clips • ${(result!['totalDuration']??0).toStringAsFixed(1)}s'),
            const SizedBox(height:8),
            Text('${result!['outputPath']??''}',textAlign:TextAlign.center),
          ]
        ])));
  }
}

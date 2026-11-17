import 'dart:convert';import 'package:flutter/material.dart';import 'package:http/http.dart' as http;
class RecentFilmsScreen extends StatefulWidget{const RecentFilmsScreen({super.key});@override State<RecentFilmsScreen> createState()=>_S();}
class _S extends State<RecentFilmsScreen>{static const base='http://10.0.2.2:3000';bool loading=true;List projects=[];
Future<void> load()async{setState(()=>loading=true);final r=await http.get(Uri.parse('$base/api/projects/recent?limit=20'));if(r.statusCode<300)setState(()=>projects=List<Map<String,dynamic>>.from(jsonDecode(r.body)['projects']??[]));if(mounted)setState(()=>loading=false);}
@override void initState(){super.initState();load();}
@override Widget build(BuildContext c)=>Scaffold(appBar:AppBar(title:const Text('Recent Films'),actions:[IconButton(onPressed:load,icon:const Icon(Icons.refresh))]),body:loading?const Center(child:CircularProgressIndicator()):ListView(padding:const EdgeInsets.all(16),children:[Text('Recently Updated',style:Theme.of(c).textTheme.headlineMedium),const SizedBox(height:12),if(projects.isEmpty)const Card(child:ListTile(title:Text('No recent films'))),...projects.map((p)=>Card(child:ListTile(leading:Icon(p['favourite']==true?Icons.star:Icons.movie),title:Text(p['title']),subtitle:Text('${p['status']} • ${p['genre']} • ${p['length']} min'),trailing:const Icon(Icons.chevron_right))))]));}
}

import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

const String reviewSummaryApi='http://10.0.2.2:3000';

class GeneratedClipReviewSummaryScreen extends StatefulWidget {
  final String projectId;
  const GeneratedClipReviewSummaryScreen({super.key,required this.projectId});
  @override State<GeneratedClipReviewSummaryScreen> createState()=>_GeneratedClipReviewSummaryScreenState();
}
class _GeneratedClipReviewSummaryScreenState extends State<GeneratedClipReviewSummaryScreen>{
  Map<String,dynamic> data={}; bool loading=true,finalizing=false; Timer? timer;
  @override void initState(){super.initState();load();timer=Timer.periodic(const Duration(seconds:4),(_)=>load());}
  @override void dispose(){timer?.cancel();super.dispose();}
  Future<void> load() async{
    try{
      final r=await http.get(Uri.parse('$reviewSummaryApi/api/projects/${widget.projectId}/generated-clips/review-summary'));
      if(r.statusCode==200&&mounted)setState(()=>data=jsonDecode(r.body));
    }finally{if(mounted)setState(()=>loading=false);}
  }
  Future<void> finalize() async{
    setState(()=>finalizing=true);
    final r=await http.post(Uri.parse('$reviewSummaryApi/api/projects/${widget.projectId}/generated-clips/review-set/finalize'));
    if(!mounted)return;
    if(r.statusCode==200){
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content:Text('Approved clips are ready for editing.')));
    }else{
      final body=jsonDecode(r.body);
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content:Text(body['error']??'Review is not ready')));
    }
    setState(()=>finalizing=false); load();
  }
  @override Widget build(BuildContext context){
    if(loading)return const Scaffold(body:Center(child:CircularProgressIndicator()));
    final ready=data['readyForEdit']==true;
    return Scaffold(appBar:AppBar(title:const Text('Review Summary')),body:ListView(padding:const EdgeInsets.all(16),children:[
      Card(child:ListTile(title:Text('${data['total']??0} generated clips'),subtitle:Text('${data['reviewed']??0} reviewed'))),
      Wrap(spacing:8,runSpacing:8,children:[
        _chip('Pending',data['pending']??0),_chip('Accepted',data['accepted']??0),
        _chip('Rejected',data['rejected']??0),_chip('Regenerate',data['needsRegeneration']??0),
        _chip('Missing',data['missing']??0)
      ]),
      const SizedBox(height:20),
      Card(child:Padding(padding:const EdgeInsets.all(16),child:Column(children:[
        Icon(ready?Icons.check_circle:Icons.pending,size:42),
        const SizedBox(height:8),
        Text(ready?'Ready for editing':'Complete clip review before editing',
          style:Theme.of(context).textTheme.titleMedium),
        const SizedBox(height:12),
        FilledButton.icon(onPressed:ready&&!finalizing?finalize:null,
          icon:finalizing?const SizedBox(width:18,height:18,child:CircularProgressIndicator(strokeWidth:2)):const Icon(Icons.lock_open),
          label:Text(finalizing?'Finalizing…':'Finalize Approved Clips'))
      ])))
    ]);}
  Widget _chip(String label,int n)=>Chip(label:Text('$label: $n'));
}

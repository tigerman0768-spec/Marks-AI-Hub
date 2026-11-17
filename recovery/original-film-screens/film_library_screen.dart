import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'film_library_player_screen.dart';
import 'film_details_screen.dart';

class FilmLibraryScreen extends StatefulWidget{
 const FilmLibraryScreen({super.key});
 @override State<FilmLibraryScreen> createState()=>_FilmLibraryScreenState();
}
class _FilmLibraryScreenState extends State<FilmLibraryScreen>{
 static const base='http://10.0.2.2:3000';
 List<dynamic> films=[];bool loading=true;final search=TextEditingController();String sort='newest';bool favouritesOnly=false;
 @override void initState(){super.initState();load();}
 Future<void> load()async{
  setState(()=>loading=true);
  try{
   final uri=Uri.parse('$base/api/film-library/search').replace(queryParameters:{
    if(search.text.trim().isNotEmpty)'q':search.text.trim(),'sort':sort,'favourite':favouritesOnly.toString()});
   final r=await http.get(uri);
   if(r.statusCode<300)setState(()=>films=List<dynamic>.from(jsonDecode(r.body)['films']??[]));
  }catch(_){}
  if(mounted)setState(()=>loading=false);
 }
 Future<void> favourite(String id)async{await http.post(Uri.parse('$base/api/film-library/$id/favourite'));load();}
 Future<void> remove(String id)async{
  final ok=await showDialog<bool>(context:context,builder:(_)=>AlertDialog(
   title:const Text('Delete film?'),content:const Text('This removes the film from the library record.'),
   actions:[TextButton(onPressed:()=>Navigator.pop(context,false),child:const Text('CANCEL')),
    FilledButton(onPressed:()=>Navigator.pop(context,true),child:const Text('DELETE'))]));
  if(ok==true){await http.delete(Uri.parse('$base/api/film-library/$id'));load();}
 }
 @override Widget build(BuildContext context)=>Scaffold(
  appBar:AppBar(title:const Text('My Film Library'),actions:[IconButton(onPressed:load,icon:const Icon(Icons.refresh))]),
  body:Column(children:[
   Padding(padding:const EdgeInsets.fromLTRB(12,12,12,4),child:TextField(controller:search,
    onSubmitted:(_)=>load(),decoration:InputDecoration(hintText:'Search films',prefixIcon:const Icon(Icons.search),
     suffixIcon:IconButton(onPressed:()=>{search.clear(),load()},icon:const Icon(Icons.clear)),border:const OutlineInputBorder()))),
   Padding(padding:const EdgeInsets.symmetric(horizontal:12,vertical:4),child:Row(children:[
    Expanded(child:DropdownButtonFormField<String>(initialValue:sort,decoration:const InputDecoration(labelText:'Sort'),
     items:const [DropdownMenuItem(value:'newest',child:Text('Newest')),DropdownMenuItem(value:'oldest',child:Text('Oldest')),
      DropdownMenuItem(value:'title',child:Text('Title')),DropdownMenuItem(value:'duration',child:Text('Longest'))],
     onChanged:(v){if(v!=null){setState(()=>sort=v);load();}})),
    const SizedBox(width:10),FilterChip(label:const Text('Favourites'),selected:favouritesOnly,
      onSelected:(v){setState(()=>favouritesOnly=v);load();})
   ])),
   Expanded(child:loading?const Center(child:CircularProgressIndicator()):
   films.isEmpty?const Center(child:Text('No finished films yet.')):
   GridView.builder(padding:const EdgeInsets.all(12),gridDelegate:const SliverGridDelegateWithFixedCrossAxisCount(
    crossAxisCount:2,crossAxisSpacing:10,mainAxisSpacing:10,childAspectRatio:.72),
    itemCount:films.length,itemBuilder:(c,i){
     final f=Map<String,dynamic>.from(films[i]);final id='${f['id']}';final title='${f['title']??'Untitled Film'}';
     return Card(clipBehavior:Clip.antiAlias,child:InkWell(onTap:()=>Navigator.push(context,MaterialPageRoute(builder:(_)=>FilmDetailsScreen(filmId:id))),child:Column(crossAxisAlignment:CrossAxisAlignment.stretch,children:[
      Expanded(child:Stack(children:[
       f['thumbnailPath']!=null && '${f['thumbnailPath']}'.isNotEmpty
        ? Image.network('$base/api/film-library/$id/thumbnail',fit:BoxFit.cover,
            errorBuilder:(_,__,___)=>const Center(child:Icon(Icons.movie,size:52)))
        : Container(color:Theme.of(context).colorScheme.surfaceContainerHighest,
            child:const Center(child:Icon(Icons.movie,size:52))),
       Positioned(right:4,top:4,child:IconButton(onPressed:()=>favourite(id),
        icon:Icon(f['favourite']==true?Icons.favorite:Icons.favorite_border))),
      ])),
      Padding(padding:const EdgeInsets.all(8),child:Text(title,maxLines:2,overflow:TextOverflow.ellipsis,
       style:const TextStyle(fontWeight:FontWeight.bold))),
      Text('${f['genre']??''} • ${f['style']??''}',maxLines:1,overflow:TextOverflow.ellipsis),
      Row(children:[
       Expanded(child:TextButton.icon(onPressed:()=>Navigator.push(context,MaterialPageRoute(
        builder:(_)=>FilmLibraryPlayerScreen(filmId:id,title:title))),icon:const Icon(Icons.play_arrow),label:const Text('PLAY'))),
       IconButton(onPressed:()=>remove(id),icon:const Icon(Icons.delete_outline)),
      ])
     ]));
    }));
  ]));
}

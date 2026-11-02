import { Component, effect, inject, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom, timeout } from 'rxjs';
import { AuthService } from '../../../core/auth.service';
interface Classroom {name:string;school:string;teacher:string;code?:string;id:number;}
interface Submission {id:number;title:string;author:string;destination:string;status:string;feedback:string|null;reviewer:string|null;created_at:string;transcript:string;feedback_revision:number;unread_feedback:boolean;}
@Component({selector:'app-practice-account',standalone:true,imports:[CommonModule,FormsModule],templateUrl:'./practice.component.html',styleUrl:'./practice.component.scss'})
export class PracticeAccountComponent implements OnDestroy {
  readonly auth=inject(AuthService); private readonly http=inject(HttpClient);
  mine:Submission[]=[];reviews:Submission[]=[];joined:Classroom|null=null;owned:Classroom[]=[];
  busy=false;error='';notice='';name='';school='';selectedSchool='';selectedFormation:number|null=null;
  available:Classroom[]=[];formationEdits:Record<number,{name:string;school:string}>={};openedFeedback:Record<number,number>={};
  private generation=0;feedback:Record<number,string>={};decisions:Record<number,string>={};
  audioUrl='';playingId:number|null=null;
  get reviewer():boolean{return ['teacher','admin'].includes(this.auth.user()?.role || '');}
  constructor(){effect(()=>{const token=this.auth.token(),user=this.auth.user();this.reset();if(token && user) void this.run(()=>this.load());});}
  get directory():Classroom[]{return this.joined && !this.available.some(item=>item.id===this.joined!.id)?[...this.available,this.joined]:this.available;}
  get schools():string[]{return [...new Set(this.directory.map(item=>item.school))].sort((a,b)=>a.localeCompare(b,'fr'));}
  get formations():Classroom[]{return this.directory.filter(item=>item.school===this.selectedSchool);}
  get unreadCount():number{return this.mine.filter(item=>item.unread_feedback).length;}
  chooseSchool():void{this.selectedFormation=null;}
  private async request<T>(method:string,path:string,body?:unknown,blob=false):Promise<T>{
    const token=this.auth.token(),generation=this.generation;if(!token) throw new Error('Reconnectez-vous.');
    const result=await firstValueFrom(this.http.request(method,'/api/practice/'+path,{body,headers:{Authorization:`Bearer ${token}`},responseType:blob?'blob':'json'}).pipe(timeout(120000)));
    if(this.auth.token()!==token || this.generation!==generation) throw new Error('Session modifiée.');return result as T;
  }
  async run(action:()=>Promise<void>):Promise<void>{
    if(this.busy)return;const generation=this.generation;this.busy=true;this.error='';this.notice='';
    try{await action();}catch{if(generation===this.generation)this.error='Action impossible. Vérifiez votre connexion et votre formation, puis réessayez.';}
    finally{if(generation===this.generation)this.busy=false;}
  }
  async load():Promise<void>{
    const generation=this.generation;
    const [classes,mine,reviews,available]=await Promise.all([
      this.request<{joined:Classroom|null;owned:Classroom[]}>('GET','classes'),this.request<Submission[]>('GET','submissions'),
      this.reviewer?this.request<Submission[]>('GET','reviews'):Promise.resolve([]),this.request<Classroom[]>('GET','classes/available')]);
    if(generation!==this.generation)return;
    this.joined=classes.joined;this.owned=classes.owned;this.mine=mine;this.reviews=reviews;this.available=available;
    this.selectedSchool=this.joined?.school || '';this.selectedFormation=this.joined?.id ?? null;
    this.formationEdits=Object.fromEntries(this.owned.map(item=>[item.id,{name:item.name,school:item.school}]));
  }
  refresh():void{void this.run(()=>this.load());}
  saveFormation():void{void this.run(async()=>{
    if(this.selectedSchool){
      if(!this.selectedFormation || !this.formations.some(item=>item.id===this.selectedFormation))throw new Error('Formation requise');
      await this.request('POST','classes/join',{class_id:this.selectedFormation});
    }else await this.request('DELETE','classes/join');
    await this.load();this.notice='Votre choix de formation est enregistré.';
  });}
  create():void{void this.run(async()=>{await this.request('POST','classes',{name:this.name,school:this.school});this.name='';await this.load();});}
  updateFormation(item:Classroom):void{void this.run(async()=>{await this.request('PATCH',`classes/${item.id}`,this.formationEdits[item.id]);await this.load();this.notice='Formation mise à jour.';});}
  readFeedback(row:Submission):void{void this.run(async()=>{
    const revision=row.feedback_revision;
    const result=await this.request<Submission>('POST',`submissions/${row.id}/read`,{revision});
    Object.assign(row,result);this.openedFeedback[row.id]=revision;
  });}
  status(value:string):string{return ({pending:'En attente',approved:'Validé',changes_requested:'À retravailler'} as Record<string,string>)[value] || value;}
  listen(row:Submission):void{void this.run(async()=>{this.stopAudio();const blob=await this.request<Blob>('GET',`submissions/${row.id}/file`,undefined,true);this.audioUrl=URL.createObjectURL(blob);this.playingId=row.id;});}
  review(row:Submission):void{void this.run(async()=>{await this.request('POST',`submissions/${row.id}/review`,{status:this.decisions[row.id] || 'approved',feedback:this.feedback[row.id]});await this.load();this.notice='Retour enregistré.';});}
  stopAudio():void{if(this.audioUrl)URL.revokeObjectURL(this.audioUrl);this.audioUrl='';this.playingId=null;}
  reset():void{this.generation++;this.busy=false;this.openedFeedback={};this.available=[];this.selectedSchool='';this.selectedFormation=null;this.mine=[];this.reviews=[];this.joined=null;this.owned=[];this.feedback={};this.decisions={};this.stopAudio();}
  ngOnDestroy():void{this.generation++;this.stopAudio();}
}

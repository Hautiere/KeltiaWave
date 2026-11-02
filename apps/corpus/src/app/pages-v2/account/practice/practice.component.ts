import { Component, effect, inject, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom, timeout } from 'rxjs';
import { AuthService } from '../../../core/auth.service';
interface Classroom {name:string;code:string;id:number;}
interface Submission {id:number;title:string;author:string;destination:string;status:string;feedback:string|null;reviewer:string|null;created_at:string;transcript:string;}
@Component({selector:'app-practice-account',standalone:true,imports:[CommonModule,FormsModule],templateUrl:'./practice.component.html',styleUrl:'./practice.component.scss'})
export class PracticeAccountComponent implements OnDestroy {
  readonly auth=inject(AuthService); private readonly http=inject(HttpClient);
  mine:Submission[]=[];reviews:Submission[]=[];joined:Classroom|null=null;owned:Classroom[]=[];
  busy=false;error='';notice='';code='';name='';feedback:Record<number,string>={};decisions:Record<number,string>={};
  audioUrl='';playingId:number|null=null;
  get reviewer():boolean{return ['teacher','admin'].includes(this.auth.user()?.role || '');}
  constructor(){effect(()=>{const token=this.auth.token();this.reset();if(token) void this.run(()=>this.load());});}
  private async request<T>(method:string,path:string,body?:unknown,blob=false):Promise<T>{
    const token=this.auth.token();if(!token) throw new Error('Reconnectez-vous.');
    const result=await firstValueFrom(this.http.request(method,'/api/practice/'+path,{body,headers:{Authorization:`Bearer ${token}`},responseType:blob?'blob':'json'}).pipe(timeout(120000)));
    if(this.auth.token()!==token) throw new Error('Session modifiée.');return result as T;
  }
  async run(action:()=>Promise<void>):Promise<void>{if(this.busy)return;this.busy=true;this.error='';this.notice='';try{await action();}catch{this.error='Action impossible. Vérifiez votre connexion et le code de classe, puis réessayez.';}finally{this.busy=false;}}
  async load():Promise<void>{const [classes,mine,reviews]=await Promise.all([this.request<{joined:Classroom|null;owned:Classroom[]}>('GET','classes'),this.request<Submission[]>('GET','submissions'),this.reviewer?this.request<Submission[]>('GET','reviews'):Promise.resolve([])]);this.joined=classes.joined;this.owned=classes.owned;this.mine=mine;this.reviews=reviews;}
  refresh():void{void this.run(()=>this.load());}
  join():void{void this.run(async()=>{await this.request('POST','classes/join',{code:this.code});this.code='';await this.load();});}
  leave():void{void this.run(async()=>{await this.request('DELETE','classes/join');await this.load();});}
  create():void{void this.run(async()=>{await this.request('POST','classes',{name:this.name});this.name='';await this.load();});}
  status(value:string):string{return ({pending:'En attente',approved:'Validé',changes_requested:'À retravailler'} as Record<string,string>)[value] || value;}
  listen(row:Submission):void{void this.run(async()=>{this.stopAudio();const blob=await this.request<Blob>('GET',`submissions/${row.id}/file`,undefined,true);this.audioUrl=URL.createObjectURL(blob);this.playingId=row.id;});}
  review(row:Submission):void{void this.run(async()=>{await this.request('POST',`submissions/${row.id}/review`,{status:this.decisions[row.id] || 'approved',feedback:this.feedback[row.id]});await this.load();this.notice='Retour enregistré.';});}
  stopAudio():void{if(this.audioUrl)URL.revokeObjectURL(this.audioUrl);this.audioUrl='';this.playingId=null;}
  reset():void{this.mine=[];this.reviews=[];this.joined=null;this.owned=[];this.feedback={};this.decisions={};this.stopAudio();}
  ngOnDestroy():void{this.stopAudio();}
}

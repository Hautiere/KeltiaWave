import { CommonModule } from '@angular/common';
import { AfterViewInit, Component, ElementRef, OnDestroy, QueryList, ViewChild, ViewChildren } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Subscription } from 'rxjs';
import { SubtitleSegment, SubtitlesApiService } from './subtitles-api.service';

type UiLanguage = 'fr'|'en'|'br'|'cy';
const LABELS: Record<string, Record<UiLanguage,string>> = {
  tools:{fr:'Autres outils',en:'Other tools',br:'Ostilhoù all',cy:'Offer eraill'},
  tagline:{fr:'Créer, caler et exporter des sous-titres',en:'Create, sync and export subtitles',br:'Krouiñ, kempouezañ hag ezporzhiañ istitloù',cy:'Creu, cysoni ac allforio isdeitlau'},
  title:{fr:'Atelier de sous-titrage',en:'Subtitle workspace',br:'Atalier istitlañ',cy:'Gweithfan isdeitlau'},
  media:{fr:'Fichier média',en:'Media file',br:'Restr media',cy:'Ffeil cyfryngau'},
  choose:{fr:'Choisir un audio ou une vidéo',en:'Choose audio or video',br:'Dibab un audio pe ur video',cy:'Dewis sain neu fideo'},
  language:{fr:'Langue',en:'Language',br:'Yezh',cy:'Iaith'},
  breton:{fr:'Breton',en:'Breton',br:'Brezhoneg',cy:'Llydaweg'},
  welsh:{fr:'Gallois',en:'Welsh',br:'Kembraeg',cy:'Cymraeg'},
  engine:{fr:'Moteur',en:'Engine',br:'Keflusker',cy:'Peiriant'},
  generate:{fr:'Générer les sous-titres',en:'Generate subtitles',br:'Krouiñ an istitloù',cy:'Creu isdeitlau'},
  import:{fr:'Importer SRT',en:'Import SRT',br:'Enporzhiañ SRT',cy:'Mewnforio SRT'},
  export:{fr:'Exporter SRT',en:'Export SRT',br:'Ezporzhiañ SRT',cy:'Allforio SRT'},
  saved:{fr:'Fichier SRT exporté',en:'SRT file exported',br:'Restr SRT ezporzhiet',cy:'Ffeil SRT wedi’i hallforio'},
  unsaved:{fr:'Modifications non enregistrées',en:'Unsaved changes',br:'Kemmoù dienrollet',cy:'Newidiadau heb eu cadw'},
  settings:{fr:'Format',en:'Format',br:'Furmad',cy:'Fformat'},
  chars:{fr:'Caractères',en:'Characters',br:'Arouezennoù',cy:'Nodau'},
  lines:{fr:'Lignes',en:'Lines',br:'Linennoù',cy:'Llinellau'},
  duration:{fr:'Durée max.',en:'Max duration',br:'Pad hirañ',cy:'Hyd mwyaf'},
  processing:{fr:'Traitement en cours…',en:'Processing…',br:'O tretiñ…',cy:'Wrthi’n prosesu…'},
  upload:{fr:'Chargement',en:'Upload',br:'O kargañ',cy:'Llwytho'},
  transcription:{fr:'Transcription estimée',en:'Estimated transcription',br:'Treuzskrivadur priziet',cy:'Trawsgrifiad amcangyfrifedig'},
  subtitles:{fr:'Sous-titres',en:'Subtitles',br:'Istitloù',cy:'Isdeitlau'},
  start:{fr:'Début',en:'Start',br:'Penn-kentañ',cy:'Dechrau'},
  end:{fr:'Fin',en:'End',br:'Dibenn',cy:'Diwedd'},
  text:{fr:'Texte',en:'Text',br:'Testenn',cy:'Testun'},
  delete:{fr:'Supprimer',en:'Delete',br:'Diverkañ',cy:'Dileu'},
  previous:{fr:'Précédent',en:'Previous',br:'Kent',cy:'Blaenorol'},
  current:{fr:'Actif',en:'Active',br:'Oberiant',cy:'Gweithredol'},
  next:{fr:'Suivant',en:'Next',br:'Da-heul',cy:'Nesaf'},
};

@Component({selector:'subtitles-root',standalone:true,imports:[CommonModule,FormsModule],templateUrl:'./subtitles-app.component.html',styleUrls:['./subtitles-app.component.scss','./subtitles-workshop.scss']})
export class SubtitlesAppComponent implements AfterViewInit,OnDestroy {
  @ViewChild('player') player?: ElementRef<HTMLVideoElement>;
  @ViewChild('cueTable') cueTable?: ElementRef<HTMLElement>;
  @ViewChildren('cueRow') cueRows?: QueryList<ElementRef<HTMLElement>>;
  readonly portalUrl = window.location.hostname.endsWith('.staging.keltiawave.com')
    ? 'https://staging.keltiawave.com/'
    : 'https://keltiawave.com/';
  ui:UiLanguage=this.initialUi(); language:'br'|'cy'='br'; engine:'vosk'|'whisper'='vosk';
  file:File|null=null; mediaUrl=''; cues:SubtitleSegment[]=[]; current=-1; busy=false; upload=0; work=0; error=''; message=''; dirty=false;
  maxChars=42; maxLines=2; maxDuration=6; private request?:Subscription; private progressTimer?:number; private nativeTrack?:TextTrack;
  constructor(private readonly api:SubtitlesApiService){}
  ngAfterViewInit(){const video=this.player?.nativeElement;if(!video)return;this.nativeTrack=video.addTextTrack('subtitles','KeltiaWave',this.language);this.nativeTrack.mode='hidden';document.addEventListener('fullscreenchange',this.syncFullscreenTrack);video.addEventListener('webkitbeginfullscreen',this.showFullscreenTrack);video.addEventListener('webkitendfullscreen',this.hideFullscreenTrack);}
  ngOnDestroy(){const video=this.player?.nativeElement;document.removeEventListener('fullscreenchange',this.syncFullscreenTrack);video?.removeEventListener('webkitbeginfullscreen',this.showFullscreenTrack);video?.removeEventListener('webkitendfullscreen',this.hideFullscreenTrack);}
  t(key:string){return LABELS[key]?.[this.ui]||key;}
  changeUi(value:string){this.ui=value as UiLanguage;localStorage.setItem('keltiawave-public-language',value);document.documentElement.lang=value;}
  choose(input:HTMLInputElement){const file=input.files?.[0];if(file)this.setMedia(file);input.value='';}
  setLanguage(value:'br'|'cy'){this.language=value;if(value==='cy')this.engine='whisper';}
  generate(){if(!this.file||this.busy)return;this.busy=true;this.error='';this.upload=0;this.work=0;this.message=this.t('processing');
    this.request=this.api.transcribe(this.file,this.language,this.engine).subscribe({next:event=>{this.upload=event.upload;if(event.upload===100&&!event.result)this.startProgress();if(event.result){this.stopProgress();this.work=100;this.cues=this.format(event.result.segments?.length?event.result.segments:[{start:0,end:this.duration||4,text:event.result.text||''}]);this.current=this.cues.length?0:-1;this.dirty=!!this.cues.length;this.refreshNativeTrack();this.busy=false;this.message=`${this.cues.length} ${this.t('subtitles')}`;}},error:error=>{this.stopProgress();this.busy=false;this.error=String(error?.error?.detail||error?.message||error);}});
  }
  importSrt(input:HTMLInputElement){const file=input.files?.[0];if(!file)return;file.text().then(text=>{this.cues=this.parseSrt(text);this.current=this.cues.length?0:-1;this.dirty=!!this.cues.length;this.refreshNativeTrack();this.message=`${this.cues.length} ${this.t('subtitles')}`;});input.value='';}
  exportSrt(){this.cues=this.cues.map(c=>({...c,start:this.roundTime(c.start),end:this.roundTime(c.end)}));const content=this.cues.map((c,i)=>`${i+1}\n${this.srtTime(c.start)} --> ${this.srtTime(c.end)}\n${c.text}`).join('\n\n');this.download(content,'keltiawave-subtitles.srt');this.refreshNativeTrack();this.dirty=false;this.message=this.t('saved');}
  reformat(){this.cues=this.format(this.cues);this.current=this.cues.length?Math.max(0,Math.min(this.current,this.cues.length-1)):-1;this.refreshNativeTrack();this.dirty=!!this.cues.length;}
  remove(index:number){this.cues.splice(index,1);this.cues=[...this.cues];this.current=this.cues.length?Math.max(0,Math.min(this.current,this.cues.length-1)):-1;this.refreshNativeTrack();this.dirty=true;}
  updateCue(index:number,text:string){if(this.cues[index]){this.cues[index].text=text;this.refreshNativeTrack();this.dirty=true;}}
  updateStart(index:number,value:number|string){const cue=this.cues[index];if(!cue)return;const minimum=index>0?this.cues[index-1].start:0;const start=Math.max(minimum,this.roundTime(value));cue.start=start;if(index>0)this.cues[index-1].end=start;if(cue.end<start){cue.end=start;if(index<this.cues.length-1)this.cues[index+1].start=start;}this.cues=[...this.cues];this.refreshNativeTrack();this.dirty=true;}
  updateEnd(index:number,value:number|string){const cue=this.cues[index];if(!cue)return;const maximum=index<this.cues.length-1?this.cues[index+1].end:Number.POSITIVE_INFINITY;const end=Math.min(maximum,Math.max(cue.start,this.roundTime(value)));cue.end=end;if(index<this.cues.length-1)this.cues[index+1].start=end;this.cues=[...this.cues];this.refreshNativeTrack();this.dirty=true;}
  seek(index:number){const cue=this.cues[index];if(!cue||!this.player)return;this.current=index;this.centerActiveCue(index);this.player.nativeElement.currentTime=cue.start;void this.player.nativeElement.play();}
  sync(){const time=this.player?.nativeElement.currentTime||0;const active=this.cues.findIndex(c=>time>=c.start&&time<c.end);if(active>=0&&active!==this.current){this.current=active;this.centerActiveCue(active);}}
  get activeText(){return this.current>=0?this.cues[this.current]?.text||'':'';}
  get previousCue(){return this.current>0?this.cues[this.current-1]:null;}
  get currentCue(){return this.current>=0?this.cues[this.current]:null;}
  get nextCue(){return this.current>=0&&this.current<this.cues.length-1?this.cues[this.current+1]:null;}
  get duration(){return this.player?.nativeElement.duration||0;}
  private setMedia(file:File){this.file=file;if(this.mediaUrl)URL.revokeObjectURL(this.mediaUrl);this.mediaUrl=URL.createObjectURL(file);this.error='';}
  private format(items:SubtitleSegment[]){const result:SubtitleSegment[]=[];for(const item of items){const words=String(item.text||'').trim().split(/\s+/).filter(Boolean);if(!words.length)continue;const blocks:string[]=[];let lines:string[]=[];let line='';for(const word of words){const next=line?`${line} ${word}`:word;if(next.length<=this.maxChars||!line)line=next;else{lines.push(line);line=word;if(lines.length===this.maxLines){blocks.push(lines.join('\n'));lines=[];}}}if(line)lines.push(line);if(lines.length)blocks.push(lines.join('\n'));const count=Math.max(blocks.length,Math.ceil(Math.max(.4,item.end-item.start)/this.maxDuration));const fallback=Math.ceil(words.length/count);const final=blocks.length===count?blocks:Array.from({length:count},(_,i)=>words.slice(i*fallback,(i+1)*fallback).join(' ')).filter(Boolean);final.forEach((text,i)=>result.push({start:this.roundTime(item.start+(item.end-item.start)*i/final.length),end:this.roundTime(item.start+(item.end-item.start)*(i+1)/final.length),text}));}return result;}
  private parseSrt(value:string){return value.replace(/\r/g,'').trim().split(/\n{2,}/).map(block=>{const rows=block.split('\n');const line=rows.findIndex(row=>row.includes('-->'));if(line<0)return null;const [a,b]=rows[line].split('-->');const start=this.parseTime(a),end=this.parseTime(b);return end>start?{start,end,text:rows.slice(line+1).join('\n').trim()}:null;}).filter((c):c is SubtitleSegment=>!!c&&!!c.text);}
  private parseTime(value:string){const m=value.trim().match(/(\d+):(\d{2}):(\d{2})[,.](\d{3})/);return this.roundTime(m?+m[1]*3600 + +m[2]*60 + +m[3] + +m[4]/1000:0);}
  private roundTime(value:number|string){const parsed=Number(value);return Math.round(Math.max(0,Number.isFinite(parsed)?parsed:0)*10)/10;}
  private srtTime(value:number){const ms=Math.round(this.roundTime(value)*1000),h=Math.floor(ms/3600000),m=Math.floor(ms%3600000/60000),s=Math.floor(ms%60000/1000);return `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')},${String(ms%1000).padStart(3,'0')}`;}
  private startProgress(){if(this.progressTimer)return;this.work=2;this.progressTimer=window.setInterval(()=>this.work=Math.min(95,this.work+2),700);}
  private stopProgress(){if(this.progressTimer)clearInterval(this.progressTimer);this.progressTimer=undefined;}
  private refreshNativeTrack(){requestAnimationFrame(()=>{const track=this.nativeTrack;if(!track)return;while(track.cues?.length)track.removeCue(track.cues[0]);for(const cue of this.cues){if(cue.end<=cue.start)continue;track.addCue(new VTTCue(cue.start,cue.end,cue.text));}});}
  private syncFullscreenTrack=()=>{const video=this.player?.nativeElement;if(this.nativeTrack)this.nativeTrack.mode=document.fullscreenElement===video?'showing':'hidden';};
  private showFullscreenTrack=()=>{if(this.nativeTrack)this.nativeTrack.mode='showing';};
  private hideFullscreenTrack=()=>{if(this.nativeTrack)this.nativeTrack.mode='hidden';};
  private centerActiveCue(index:number){requestAnimationFrame(()=>{const container=this.cueTable?.nativeElement,row=this.cueRows?.get(index)?.nativeElement;if(!container||!row)return;const box=container.getBoundingClientRect(),item=row.getBoundingClientRect();const top=container.scrollTop+(item.top-box.top)-(container.clientHeight-item.height)/2;container.scrollTo({top:Math.max(0,top),behavior:'smooth'});});}
  private download(text:string,name:string){const url=URL.createObjectURL(new Blob([text],{type:'application/x-subrip'}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url));}
  private initialUi():UiLanguage{const value=localStorage.getItem('keltiawave-public-language')||'fr';return ['fr','en','br','cy'].includes(value)?value as UiLanguage:'fr';}
}
